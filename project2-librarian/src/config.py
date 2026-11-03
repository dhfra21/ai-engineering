"""Settings and the price table used for the cost model (USD per million tokens).

LLM_PROVIDER picks the API: "openai" (default, key from the course) or "groq".
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PROVIDER = os.getenv("LLM_PROVIDER", "openai")
PROVIDERS = {
    "openai": {"url": "https://api.openai.com/v1/chat/completions", "key_env": "OPENAI_API_KEY",
               "generator": "gpt-4o-mini", "judge": "gpt-4.1-mini"},
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "key_env": "GROQ_API_KEY",
             "generator": "llama-3.3-70b-versatile", "judge": "llama-3.3-70b-versatile"},
}
_P = PROVIDERS[PROVIDER]
LLM_URL = _P["url"]
GENERATOR = os.getenv("GENERATOR_MODEL", _P["generator"])
JUDGE = os.getenv("JUDGE_MODEL", _P["judge"])

# List prices; check the provider's pricing page before quoting them in the report
PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5-nano": (0.05, 0.40),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}


def api_key():
    key = os.getenv(_P["key_env"])
    if not key:
        raise RuntimeError(f"{_P['key_env']} is not set: copy .env.example to .env and add the key")
    return key


def cost_usd(model, prompt_tokens, completion_tokens):
    p_in, p_out = PRICES.get(model, (0.0, 0.0))
    return (prompt_tokens * p_in + completion_tokens * p_out) / 1e6
