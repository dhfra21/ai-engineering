"""Thin, uniform wrappers around the backends used in the bake-off: Groq
(top + cheap model, on its free tier), a local Ollama server (the
open-weights model you run yourself), and — kept for reference, unused by
default — the Anthropic and Gemini APIs, in case you swap a model back in.

Every call returns the same shape so run.py doesn't need to branch:
    {
        "raw_output": str,
        "latency_ms": float,
        "input_tokens": int | None,
        "output_tokens": int | None,
        "tokens_per_second": float | None,   # only meaningful for Ollama
        "error": str | None,
    }

The Anthropic and Google SDKs are imported lazily inside their respective
call_*() functions rather than at module level, so this file — and a
`python -m src.run` that only touches Groq + Ollama — doesn't need those
packages installed. See requirements.txt.
"""
from __future__ import annotations

import random
import re
import time
from typing import Any

import requests

from src.config import MAX_OUTPUT_TOKENS, OLLAMA_BASE_URL, ModelSpec
from src.prompt import SYSTEM_PROMPT, build_prompt

CallResult = dict[str, Any]

_RETRY_AFTER_RE = re.compile(r"retry in (\d+(?:\.\d+)?)s", re.IGNORECASE)


def _suggested_retry_delay(exc: Exception) -> float | None:
    match = _RETRY_AFTER_RE.search(str(exc))
    return float(match.group(1)) if match else None


def _empty_result(error: str) -> CallResult:
    return {
        "raw_output": "",
        "latency_ms": None,
        "input_tokens": None,
        "output_tokens": None,
        "tokens_per_second": None,
        "error": error,
    }


def call_claude(spec: ModelSpec, question: str, client) -> CallResult:
    """client is an anthropic.Anthropic() instance, passed in so run.py
    creates it once and reuses the connection across all 50 calls."""
    prompt = build_prompt(question)
    kwargs: dict[str, Any] = dict(
        model=spec.model_id,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    # Claude Opus 5 rejects temperature/top_p/top_k entirely (sampling was
    # removed in favor of adaptive thinking + effort). Haiku 4.5 still
    # accepts temperature, so we pin it there for the closest thing to a
    # like-for-like "temperature 0" setting the brief asks for. This is a
    # deliberate, documented deviation — see README.md / postmortem.md.
    if spec.key != "opus5":
        kwargs["temperature"] = 0

    start = time.perf_counter()
    try:
        response = client.messages.create(**kwargs)
    except Exception as e:  # noqa: BLE001 — record every failure as a scored item, not a crash
        return _empty_result(f"{type(e).__name__}: {e}")
    latency_ms = (time.perf_counter() - start) * 1000

    if response.stop_reason == "refusal":
        return {
            "raw_output": "",
            "latency_ms": latency_ms,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "tokens_per_second": None,
            "error": f"refusal: {getattr(response.stop_details, 'category', None)}",
        }

    text = "".join(b.text for b in response.content if b.type == "text")
    return {
        "raw_output": text,
        "latency_ms": latency_ms,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "tokens_per_second": None,
        "error": None,
    }


def call_gemini(spec: ModelSpec, question: str, client) -> CallResult:
    """Not used by default (see src/config.py) — kept for reference.
    client is a google.genai.Client() instance, passed in so run.py
    creates it once and reuses it across all 50 calls. Reads
    GEMINI_API_KEY from the environment automatically.

    Retries on 429 (rate limit) and 5xx (transient server errors) using
    the server's own suggested wait when it provides one, falling back to
    exponential backoff otherwise. A quota hit is Google's infrastructure,
    not the model failing the question — it shouldn't get scored as wrong
    just because we asked faster than the free tier allows."""
    from google.genai import errors as genai_errors  # lazy: optional dependency
    from google.genai import types as genai_types

    retryable_codes = {429, 500, 502, 503, 504}
    max_retries = 6
    backoff_cap_s = 90.0

    prompt = build_prompt(question)
    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    response = None
    error_to_report = None
    latency_ms = None
    for attempt in range(max_retries + 1):
        # Timed per attempt, not across the whole retry loop — rate-limit
        # backoff sleeps are Google's free-tier quota, not the model's
        # response time, and must not leak into the latency numbers.
        attempt_start = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=spec.model_id,
                contents=prompt,
                config=config,
            )
            latency_ms = (time.perf_counter() - attempt_start) * 1000
            error_to_report = None
            break
        except genai_errors.APIError as e:
            latency_ms = (time.perf_counter() - attempt_start) * 1000
            error_to_report = f"{type(e).__name__}: {e}"
            code = getattr(e, "code", None)
            if code in retryable_codes and attempt < max_retries:
                delay = _suggested_retry_delay(e)
                if delay is None:
                    delay = min(2 ** attempt, backoff_cap_s)
                delay = min(delay + random.uniform(0.5, 2.0), backoff_cap_s)
                print(f"    [{spec.key}] {code} — retrying in {delay:.0f}s "
                      f"(attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            break
        except Exception as e:  # noqa: BLE001 — record every failure as a scored item, not a crash
            latency_ms = (time.perf_counter() - attempt_start) * 1000
            error_to_report = f"{type(e).__name__}: {e}"
            break

    if response is None:
        return {
            "raw_output": "",
            "latency_ms": latency_ms,
            "input_tokens": None,
            "output_tokens": None,
            "tokens_per_second": None,
            "error": error_to_report or "unknown error",
        }

    usage = response.usage_metadata
    return {
        "raw_output": response.text or "",
        "latency_ms": latency_ms,
        "input_tokens": usage.prompt_token_count if usage else None,
        "output_tokens": usage.candidates_token_count if usage else None,
        "tokens_per_second": None,
        "error": None,
    }


def call_groq(spec: ModelSpec, question: str, client) -> CallResult:
    """client is a groq.Groq() instance, created once in run.py and
    reused across all 50 calls. Reads GROQ_API_KEY from the environment
    automatically.

    Unlike the Gemini client, the Groq SDK retries 429/5xx itself,
    honoring the server's Retry-After header (see run.py for where
    max_retries is set) — no manual backoff loop needed here."""
    prompt = build_prompt(question)

    start = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=spec.model_id,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
    except Exception as e:  # noqa: BLE001 — record every failure as a scored item, not a crash
        return _empty_result(f"{type(e).__name__}: {e}")
    latency_ms = (time.perf_counter() - start) * 1000

    text = response.choices[0].message.content or ""
    usage = response.usage
    return {
        "raw_output": text,
        "latency_ms": latency_ms,
        "input_tokens": usage.prompt_tokens if usage else None,
        "output_tokens": usage.completion_tokens if usage else None,
        "tokens_per_second": None,
        "error": None,
    }


def call_ollama(spec: ModelSpec, question: str) -> CallResult:
    prompt = build_prompt(question)
    payload = {
        "model": spec.model_id,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": MAX_OUTPUT_TOKENS,
        },
    }
    start = time.perf_counter()
    try:
        resp = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        return _empty_result(f"{type(e).__name__}: {e}")
    latency_ms = (time.perf_counter() - start) * 1000

    eval_count = data.get("eval_count")
    eval_duration_ns = data.get("eval_duration")
    tps = None
    if eval_count and eval_duration_ns:
        tps = eval_count / (eval_duration_ns / 1e9)

    return {
        "raw_output": data.get("response", ""),
        "latency_ms": latency_ms,
        "input_tokens": data.get("prompt_eval_count"),
        "output_tokens": eval_count,
        "tokens_per_second": tps,
        "error": None,
    }
