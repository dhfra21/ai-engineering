"""Settings and the price table used for the cost model (USD per million tokens)."""
import os
from pathlib import Path

from dotenv import load_dotenv  # noqa: F401  (loaded below if available)

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GENERATOR = os.getenv("GENERATOR_MODEL", "llama-3.3-70b-versatile")
JUDGE = os.getenv("JUDGE_MODEL", "llama-3.3-70b-versatile")

# Groq list prices; check https://groq.com/pricing before quoting in the report
PRICES = {
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}


def groq_key():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set: copy .env.example to .env and add a key")
    return key


def cost_usd(model, prompt_tokens, completion_tokens):
    p_in, p_out = PRICES.get(model, (0.0, 0.0))
    return (prompt_tokens * p_in + completion_tokens * p_out) / 1e6
