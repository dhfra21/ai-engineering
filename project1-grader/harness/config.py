"""Models, prices, paths. The one place to change which model plays which role.

All models run on Groq's free tier (console.groq.com — no card; limits are
per model, roughly 30 requests/minute and 1,000 requests/day, plus a daily
token cap — check https://console.groq.com/docs/rate-limits). $0 is spent
collecting results; the prices below are Groq's published *paid* rates, so
the cost model (harness/cost.py) reflects what the same traffic would cost
once it outgrows the free tier.

Pricing and model ids checked: 2026-09-22 against
https://console.groq.com/docs/models — re-check before you submit.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "db" / "store.db"
QUERIES_PATH = ROOT / "data" / "queries.jsonl"
CANDIDATES_PATH = ROOT / "data" / "candidates.jsonl"
GOLDEN_PATH = ROOT / "data" / "golden.jsonl"
LABELS_DIR = ROOT / "data" / "labels"
PROMPTS_DIR = ROOT / "prompts"
RESULTS_DIR = ROOT / "results"
CACHE_DIR = ROOT / ".cache" / "llm"


@dataclass(frozen=True)
class ModelSpec:
    key: str                      # short id used in result files
    model_id: str                 # exact string sent to the API
    input_price_per_mtok: float   # USD per 1M input tokens (Groq paid tier)
    output_price_per_mtok: float  # USD per 1M output tokens (includes reasoning tokens)
    rpm: int = 30                 # free-tier requests/minute, used for client-side pacing
    structured: str = "json_schema"   # "json_schema" (strict) or "json_object" (validated locally)
    extra: dict = field(default_factory=dict)  # model-specific request params


MODELS: dict[str, ModelSpec] = {
    m.key: m for m in [
        ModelSpec("gptoss20b", "openai/gpt-oss-20b", 0.075, 0.30,
                  extra={"reasoning_effort": "low"}),
        ModelSpec("gptoss120b", "openai/gpt-oss-120b", 0.15, 0.60,
                  extra={"reasoning_effort": "medium"}),
        ModelSpec("llama8b", "llama-3.1-8b-instant", 0.05, 0.08,
                  structured="json_object"),
    ]
}

SYSTEM_MODEL = "gptoss20b"    # the system under test
JUDGE_MODEL = "gptoss120b"    # the LLM judge
WEAK_MODEL = "llama8b"        # only used to make candidate answers for labelling
PERTURB_MODEL = "gptoss120b"  # only used to plant errors in candidate answers
PAD_MODEL = "gptoss20b"       # only used for the verbosity-bias check

TEMPERATURE = 0
# Reasoning tokens count against this budget on gpt-oss, so it is not tight.
MAX_TOKENS = {"system": 1024, "judge": 1536, "pairwise": 1536, "perturb": 1536, "pad": 1536}

# Same schema text Project 0 used, so explanations can name real columns.
SCHEMA_TEXT = """\
Table categories(category_id INTEGER PK, name TEXT)
Table customers(customer_id INTEGER PK, name TEXT, city TEXT, country TEXT, signup_date TEXT "YYYY-MM-DD")
Table products(product_id INTEGER PK, name TEXT, category_id INTEGER FK->categories.category_id, price REAL, in_stock INTEGER "0 or 1")
Table orders(order_id INTEGER PK, customer_id INTEGER FK->customers.customer_id, order_date TEXT "YYYY-MM-DD", status TEXT "completed|pending|cancelled")
Table order_items(order_item_id INTEGER PK, order_id INTEGER FK->orders.order_id, product_id INTEGER FK->products.product_id, quantity INTEGER, unit_price REAL "price at time of order")
"""


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader (KEY=VALUE lines) so the project needs no pip installs.
    Never overrides a variable that is already set in the environment."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def is_mock() -> bool:
    """GRADER_BACKEND=mock swaps every API call for a fake, deterministic answer.
    Used by the tests and for trying the pipeline without a key. Mock results
    are written under results/mock/ and never mixed with real ones."""
    return os.environ.get("GRADER_BACKEND", "groq").lower() == "mock"


def results_root() -> Path:
    return RESULTS_DIR / "mock" if is_mock() else RESULTS_DIR
