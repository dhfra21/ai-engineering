"""One function every other module uses to call a model: `call_json`.

- Talks to Groq's OpenAI-compatible endpoint with urllib (no SDK, no pip).
- Asks for structured output: strict `json_schema` where the model supports
  it, else `json_object` mode. Either way the reply is parsed and validated
  locally against the same schema (harness/schemas.py). A reply that fails
  validation is retried once, then recorded as an error — never guessed at.
- Caches every successful response on disk (.cache/llm/, git-ignored), keyed
  by the exact request. Re-running a command after hitting the daily limit
  resumes where it stopped instead of re-spending quota. Pass use_cache=False
  to force fresh calls.
- Paces requests to the free-tier requests/minute limit and retries 429/5xx.
  If Groq says to wait longer than MAX_WAIT_S (the daily cap), it raises
  DailyLimitReached so the caller can stop cleanly.

Every call returns an LLMResult, including failures, so a bad call becomes a
row in the results with its error — not a crash, and not a silent zero.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from harness import schemas
from harness.config import CACHE_DIR, MODELS, TEMPERATURE, ModelSpec, is_mock, load_dotenv

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_RETRIES = 6
MAX_WAIT_S = 120.0
TIMEOUT_S = 120

load_dotenv()

# Models that rejected json_schema at runtime fall back to json_object for the
# rest of the process (and say so once).
_json_object_fallback: set[str] = set()
_last_call_at: dict[str, float] = {}


class DailyLimitReached(RuntimeError):
    pass


@dataclass
class LLMResult:
    model_key: str
    data: dict | None          # parsed, schema-valid JSON — None if the call failed
    raw: str                   # the model's raw text (kept for debugging)
    input_tokens: int
    output_tokens: int
    latency_ms: float | None
    error: str | None = None
    cached: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None and self.data is not None

    @property
    def cost_usd(self) -> float:
        spec = MODELS[self.model_key]
        return (self.input_tokens * spec.input_price_per_mtok
                + self.output_tokens * spec.output_price_per_mtok) / 1_000_000


def call_json(model_key: str, messages: list[dict], schema_name: str, max_tokens: int,
              use_cache: bool = True) -> LLMResult:
    spec = MODELS[model_key]
    schema = schemas.BY_NAME[schema_name]
    if is_mock():
        return _mock_call(spec, messages, schema_name)

    last: LLMResult | None = None
    for attempt in range(2):  # one retry if the reply violates the schema
        payload = _payload(spec, messages, schema_name, schema, max_tokens)
        result = _cached_or_live(spec, payload, use_cache=use_cache and attempt == 0)
        if result.error:
            return result
        try:
            data = json.loads(result.raw)
            schemas.validate(data, schema)
            result.data = data
            if not result.cached:
                _cache_write(payload, result)
            return result
        except (json.JSONDecodeError, schemas.SchemaError) as e:
            result.error = f"schema_violation: {e}"
            last = result
    return last  # type: ignore[return-value]


# --------------------------------------------------------------------------- request

def _payload(spec: ModelSpec, messages: list[dict], schema_name: str, schema: dict,
             max_tokens: int) -> dict:
    mode = "json_object" if spec.key in _json_object_fallback else spec.structured
    msgs = [dict(m) for m in messages]
    if mode == "json_schema":
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        }
    else:
        # json_object mode only guarantees *some* JSON, so the schema goes in the prompt.
        msgs[0]["content"] += (
            "\n\nRespond with a single JSON object that matches this JSON Schema exactly, "
            "and nothing else:\n" + json.dumps(schema)
        )
        response_format = {"type": "json_object"}
    return {
        "model": spec.model_id,
        "messages": msgs,
        "temperature": TEMPERATURE,
        "max_completion_tokens": max_tokens,
        "response_format": response_format,
        **spec.extra,
    }


def _cached_or_live(spec: ModelSpec, payload: dict, use_cache: bool) -> LLMResult:
    if use_cache:
        hit = _cache_read(payload)
        if hit is not None:
            return LLMResult(spec.key, None, hit["raw"], hit["input_tokens"],
                             hit["output_tokens"], hit["latency_ms"], cached=True)
    return _live_call(spec, payload)


def _live_call(spec: ModelSpec, payload: dict) -> LLMResult:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SystemExit("GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
                         "(free at console.groq.com/keys), or set GRADER_BACKEND=mock to try "
                         "the pipeline offline.")

    for attempt in range(MAX_RETRIES + 1):
        _pace(spec)
        req = urllib.request.Request(
            GROQ_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                # Groq sits behind Cloudflare, which blocks the default Python-urllib agent.
                "User-Agent": "cs496-grader/1.0",
            },
            method="POST",
        )
        # Timed per attempt so rate-limit sleeps never leak into latency numbers.
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                body = json.loads(resp.read())
            latency_ms = (time.perf_counter() - start) * 1000
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            if e.code == 400 and "response_format" in detail and spec.key not in _json_object_fallback:
                print(f"    [{spec.key}] json_schema rejected — falling back to json_object mode")
                _json_object_fallback.add(spec.key)
                return _live_call(spec, _payload_to_json_object(spec, payload))
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = _retry_after(e, attempt)
                if e.code == 429 and wait > MAX_WAIT_S:
                    raise DailyLimitReached(
                        f"{spec.model_id}: Groq asks to wait {wait:.0f}s — probably the daily "
                        f"request/token cap. Completed calls are cached; rerun the same command "
                        f"later and it resumes. ({detail[:200]})")
                print(f"    [{spec.key}] HTTP {e.code} — retrying in {wait:.0f}s "
                      f"(attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            return LLMResult(spec.key, None, "", 0, 0, None, error=f"HTTP {e.code}: {detail}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < MAX_RETRIES:
                time.sleep(min(2 ** attempt, 30))
                continue
            return LLMResult(spec.key, None, "", 0, 0, None, error=f"{type(e).__name__}: {e}")

        choice = body["choices"][0]
        usage = body.get("usage") or {}
        result = LLMResult(
            spec.key, None, choice["message"].get("content") or "",
            usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), latency_ms,
        )
        if choice.get("finish_reason") == "length":
            result.error = "truncated: hit max_completion_tokens"
        return result
    raise AssertionError("unreachable")


def _payload_to_json_object(spec: ModelSpec, payload: dict) -> dict:
    schema = payload["response_format"]["json_schema"]["schema"]
    name = payload["response_format"]["json_schema"]["name"]
    original = [dict(m) for m in payload["messages"]]
    return _payload(spec, original, name, schema, payload["max_completion_tokens"])


def _pace(spec: ModelSpec) -> None:
    gap = 60.0 / spec.rpm
    since = time.monotonic() - _last_call_at.get(spec.key, 0.0)
    if since < gap:
        time.sleep(gap - since)
    _last_call_at[spec.key] = time.monotonic()


def _retry_after(e: urllib.error.HTTPError, attempt: int) -> float:
    header = e.headers.get("retry-after") if e.headers else None
    try:
        if header is not None:
            return float(header) + random.uniform(0.5, 1.5)
    except ValueError:
        pass
    return min(2 ** attempt, 60) + random.uniform(0.5, 1.5)


# --------------------------------------------------------------------------- cache

def _cache_path(payload: dict):
    key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return CACHE_DIR / key[:2] / f"{key}.json"


def _cache_read(payload: dict) -> dict | None:
    path = _cache_path(payload)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _cache_write(payload: dict, result: LLMResult) -> None:
    path = _cache_path(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "model": payload["model"],
        "raw": result.raw,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "latency_ms": result.latency_ms,
    }), encoding="utf-8")


# --------------------------------------------------------------------------- mock

def _mock_call(spec: ModelSpec, messages: list[dict], schema_name: str) -> LLMResult:
    """Deterministic fake replies, shaped like the real ones. Not a model: the
    grades are hash-based noise. Exists so the pipeline can be tested offline."""
    text = "\n".join(m["content"] for m in messages)
    h = int(hashlib.sha256(text.encode()).hexdigest(), 16)
    data: dict[str, Any]
    if schema_name == "system":
        data = {"explanation": f"[mock] This query returns rows from the database ({h % 97} words of detail)."}
    elif schema_name == "judge":
        good = h % 10 < 6
        data = {"reason": "[mock] hash-based grade", "failed_criteria": [] if good else [schemas.CRITERIA[h % 4]],
                "grade": "good" if good else "bad"}
    elif schema_name == "pairwise":
        data = {"reason": "[mock] hash-based winner", "winner": ["A", "A", "B", "B", "tie"][h % 5]}
    elif schema_name == "perturb":
        data = {"explanation": "[mock] This query returns rows, but only for 2023.",
                "change_made": "[mock] invented a date filter"}
    elif schema_name == "pad":
        data = {"explanation": "[mock] Great question! " + "Padding sentence. " * (3 + h % 5)}
    else:
        raise ValueError(schema_name)
    schemas.validate(data, schemas.BY_NAME[schema_name])
    raw = json.dumps(data)
    return LLMResult(spec.key, data, raw, len(text) // 4, len(raw) // 4, float(200 + h % 800))
