"""Settings, stop-rule limits and the price table (USD per million tokens)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PROVIDER = os.getenv("LLM_PROVIDER", "openai")
PROVIDERS = {
    "openai": {"url": "https://api.openai.com/v1/chat/completions", "key_env": "OPENAI_API_KEY", "model": "gpt-4o-mini"},
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "key_env": "GROQ_API_KEY", "model": "openai/gpt-oss-120b"},
}
_P = PROVIDERS[PROVIDER]
LLM_URL = _P["url"]
MODEL = os.getenv("AGENT_MODEL", _P["model"])
PRICES = {"gpt-4o-mini": (0.15, 0.60), "gpt-4.1-mini": (0.40, 1.60),   # USD per million tokens (in, out);
          "openai/gpt-oss-120b": (0.15, 0.60)}                       # check the pricing pages before quoting

# Stop rule: whichever limit is hit first ends the run. Tested in tests/test_loop.py
MAX_STEPS = int(os.getenv("MAX_STEPS", "12"))
MAX_COST_USD = float(os.getenv("MAX_COST_USD", "0.05"))
MAX_REPEAT_CALLS = 3        # same tool + arguments + result this many times in a row = stuck

DB_PATH = Path(os.getenv("MAILBOX_DB", ROOT / "sandbox" / "mailbox.db"))
SEED_PATH = ROOT / "sandbox" / "seed.json"
LOG_PATH = ROOT / "results" / "trajectories.jsonl"


def api_key():
    key = os.getenv(_P["key_env"])
    if not key:
        raise RuntimeError(f"{_P['key_env']} is not set: copy .env.example to .env and add the key")
    return key
