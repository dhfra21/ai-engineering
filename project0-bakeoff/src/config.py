"""Model + pricing configuration for the bake-off.

Prices are per the Anthropic API price list and Ollama's local (self-hosted)
model. Update PRICES if you swap in different models — the brief requires
writing down the exact model name and the date you ran the eval, so do that
in README.md's results table, not just here.

Pricing checked: 2026-09-22 (see Anthropic's pricing page for current rates).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    key: str            # short id used in results/per_item.csv
    kind: str            # "anthropic" | "ollama"
    model_id: str        # exact model string passed to the API / Ollama
    role: str             # "top_api" | "cheap_api" | "open_weights"
    input_price_per_mtok: float | None   # USD per 1,000,000 input tokens (API only)
    output_price_per_mtok: float | None  # USD per 1,000,000 output tokens (API only)


MODELS: list[ModelSpec] = [
    ModelSpec(
        key="opus5",
        kind="anthropic",
        model_id="claude-opus-5",
        role="top_api",
        input_price_per_mtok=5.00,
        output_price_per_mtok=25.00,
    ),
    ModelSpec(
        key="haiku45",
        kind="anthropic",
        model_id="claude-haiku-4-5",
        role="cheap_api",
        input_price_per_mtok=1.00,
        output_price_per_mtok=5.00,
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

MODEL_BY_KEY = {m.key: m for m in MODELS}

# Hard cap requested by the brief so a bad prompt can't runaway-generate.
MAX_OUTPUT_TOKENS = 512

# Ollama's local HTTP server (default install).
OLLAMA_BASE_URL = "http://localhost:11434"

DB_PATH = "db/store.db"
ITEMS_PATH = "data/items.jsonl"
RESULTS_DIR = "results"
