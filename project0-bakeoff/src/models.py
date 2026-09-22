"""Thin, uniform wrappers around the backends used in the bake-off: the
Gemini API (top + cheap model, on Google AI Studio's free tier), a local
Ollama server (the open-weights model you run yourself), and — kept for
reference — the Anthropic API, in case you get API access later.

Every call returns the same shape so run.py doesn't need to branch:
    {
        "raw_output": str,
        "latency_ms": float,
        "input_tokens": int | None,
        "output_tokens": int | None,
        "tokens_per_second": float | None,   # only meaningful for Ollama
        "error": str | None,
    }
"""
from __future__ import annotations

import time
from typing import Any

import requests
from google.genai import types as genai_types

from src.config import MAX_OUTPUT_TOKENS, OLLAMA_BASE_URL, ModelSpec
from src.prompt import SYSTEM_PROMPT, build_prompt

CallResult = dict[str, Any]


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
    """client is a google.genai.Client() instance, passed in so run.py
    creates it once and reuses it across all 50 calls. Reads
    GEMINI_API_KEY from the environment automatically."""
    prompt = build_prompt(question)
    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    start = time.perf_counter()
    try:
        response = client.models.generate_content(
            model=spec.model_id,
            contents=prompt,
            config=config,
        )
    except Exception as e:  # noqa: BLE001 — record every failure as a scored item, not a crash
        return _empty_result(f"{type(e).__name__}: {e}")
    latency_ms = (time.perf_counter() - start) * 1000

    usage = response.usage_metadata
    return {
        "raw_output": response.text or "",
        "latency_ms": latency_ms,
        "input_tokens": usage.prompt_token_count if usage else None,
        "output_tokens": usage.candidates_token_count if usage else None,
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
