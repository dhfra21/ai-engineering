"""Model + pricing configuration for the bake-off.

The two API-tier models run on Google AI Studio's Gemini API, which has a
genuinely free tier (no credit card) for these two models — see
https://ai.google.dev/gemini-api/docs/pricing. Actual $ spent collecting
results is $0. The prices below are still the published *paid* list rate,
because the brief asks for cost computed from "the usage field of the real
answers x the list price" — using the list price (not $0) is also what
makes the "cost at 100x traffic" projection in the report meaningful: at
that volume you'd be well past any free quota and paying the real rate.

Update this file if you swap in different models — the brief requires
writing down the exact model name and the date you ran the eval, so do
that in README.md's results table too, not just here.

Pricing checked: 2026-09-22 (see https://ai.google.dev/gemini-api/docs/pricing
for current rates — Google revises free-tier limits and list prices
periodically, so re-check before you submit).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    key: str            # short id used in results/per_item.csv
    kind: str            # "google" | "anthropic" | "ollama"
    model_id: str        # exact model string passed to the API / Ollama
    role: str             # "top_api" | "cheap_api" | "open_weights"
    input_price_per_mtok: float | None   # USD per 1,000,000 input tokens (API only)
    output_price_per_mtok: float | None  # USD per 1,000,000 output tokens (API only)


MODELS: list[ModelSpec] = [
    ModelSpec(
        key="gemini38flash",
        kind="google",
        model_id="gemini-3.8-flash",
        role="top_api",
        input_price_per_mtok=0.75,
        output_price_per_mtok=3.75,
    ),
    ModelSpec(
        key="gemini35flashlite",
        kind="google",
        model_id="gemini-3.5-flash-lite",
        role="cheap_api",
        input_price_per_mtok=0.30,
        output_price_per_mtok=2.50,
    ),
    ModelSpec(
        key="qwen7b",
        kind="ollama",
        model_id="qwen2.5-coder:7b-instruct",
        role="open_weights",
        input_price_per_mtok=None,   # no per-token API price — see cost.py
        output_price_per_mtok=None,
    ),
]

# Kept for reference / in case you get Anthropic API access later and want
# to swap a model back in — src/models.py::call_claude still supports it.
# ANTHROPIC_ALTERNATIVES = [
#     ModelSpec(key="opus5", kind="anthropic", model_id="claude-opus-5",
#                role="top_api", input_price_per_mtok=5.00, output_price_per_mtok=25.00),
#     ModelSpec(key="haiku45", kind="anthropic", model_id="claude-haiku-4-5",
#                role="cheap_api", input_price_per_mtok=1.00, output_price_per_mtok=5.00),
# ]

MODEL_BY_KEY = {m.key: m for m in MODELS}

# Hard cap requested by the brief so a bad prompt can't runaway-generate.
MAX_OUTPUT_TOKENS = 512

# Ollama's local HTTP server (default install).
OLLAMA_BASE_URL = "http://localhost:11434"

DB_PATH = "db/store.db"
ITEMS_PATH = "data/items.jsonl"
RESULTS_DIR = "results"
