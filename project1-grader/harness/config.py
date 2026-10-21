"""Models, prices, paths. The one place to change which model plays which role.

All models run on the OpenAI API, with the key the instructor provided.
Rate limits depend on the key's usage tier
(https://platform.openai.com/settings/organization/limits). The prices below
are OpenAI's standard (non-batch) list rates and feed the cost model
(harness/cost.py).

Model ids checked against /v1/models for our key on 2026-10-20. Prices are
from https://openai.com/api/pricing — re-check before you submit.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Windows consoles default to cp1252, which can't print the arrows and Greek
# letters in our reports. Every harness module imports this one, so fix it here.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

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
    input_price_per_mtok: float   # USD per 1M input tokens
    output_price_per_mtok: float  # USD per 1M output tokens (includes reasoning tokens)
    rpm: int = 300                # requests/minute, used for client-side pacing
    structured: str = "json_schema"   # "json_schema" (strict) or "json_object" (validated locally)
    temperature: bool = True      # reasoning models (gpt-5 family) reject `temperature`
    extra: dict = field(default_factory=dict)  # model-specific request params


MODELS: dict[str, ModelSpec] = {
    m.key: m for m in [
        ModelSpec("gpt5nano", "gpt-5-nano", 0.05, 0.40, temperature=False,
                  extra={"reasoning_effort": "low"}),
        # Same model as the system, thinking harder. Used only as a labeller.
        ModelSpec("gpt5nanohigh", "gpt-5-nano", 0.05, 0.40, temperature=False,
                  extra={"reasoning_effort": "high"}),
        ModelSpec("gpt5mini", "gpt-5-mini", 0.25, 2.00, temperature=False,
                  extra={"reasoning_effort": "medium"}),
        # Non-reasoning and older, so its candidates make more natural errors.
        ModelSpec("gpt4omini", "gpt-4o-mini", 0.15, 0.60),
    ]
}

SYSTEM_MODEL = "gpt5nano"     # the system under test
JUDGE_MODEL = "gpt5mini"      # the LLM judge
WEAK_MODEL = "gpt4omini"      # only used to make candidate answers for labelling
PERTURB_MODEL = "gpt5mini"    # only used to plant errors in candidate answers
PAD_MODEL = "gpt5nano"        # only used for the verbosity-bias check
# The two labellers that make the golden set (approved by the instructor in
# place of two human labellers; humans adjudicate where they disagree).
# Neither is the judge, or judge/label agreement would be self-agreement.
LABELLER_MODELS = ["gpt4omini", "gpt5nanohigh"]

TEMPERATURE = 0  # sent only to models with temperature=True
# Reasoning tokens count against this budget on gpt-5, so it is not tight.
MAX_TOKENS = {"system": 2048, "judge": 4096, "pairwise": 4096, "perturb": 1536, "pad": 1536,
              "label": 4096}

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
    return os.environ.get("GRADER_BACKEND", "openai").lower() == "mock"


def results_root() -> Path:
    return RESULTS_DIR / "mock" if is_mock() else RESULTS_DIR
