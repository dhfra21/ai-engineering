"""Model + pricing configuration for the bake-off.

The two API-tier models run on Groq (console.groq.com), which has a
genuinely free tier (no credit card) with generous limits for both models
below — 30 requests/minute, 1,000 requests/day, per
https://console.groq.com/docs/rate-limits. Actual $ spent collecting
results is $0. The prices below are still the published *paid* list rate,
because the brief asks for cost computed from "the usage field of the real
answers x the list price" — using the list price (not $0) is also what
makes the "cost at 100x traffic" projection in the report meaningful: at
that volume you'd be well past the free tier's daily request cap and
paying (or needing to upgrade to) the real rate.

Both models happen to be the same OpenAI GPT-OSS family at two sizes
(120B vs 20B) rather than two different providers/architectures — that's
a deliberate, documented choice (see postmortem.md), not an accident.
It still satisfies the brief's "top API model" / "cheap API model" split:
same relationship (you call an API, you don't run the weights), same
provider, just two different capability/cost tiers Groq itself sells.

Update this file if you swap in different models — the brief requires
writing down the exact model name and the date you ran the eval, so do
that in README.md's results table too, not just here.

Pricing checked: 2026-09-22 (see https://console.groq.com/docs/models
for current rates — re-check before you submit, providers revise these).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    key: str            # short id used in results/per_item.csv
    kind: str            # "groq" | "google" | "anthropic" | "ollama"
    model_id: str        # exact model string passed to the API / Ollama
    role: str             # "top_api" | "cheap_api" | "open_weights"
    input_price_per_mtok: float | None   # USD per 1,000,000 input tokens (API only)
    output_price_per_mtok: float | None  # USD per 1,000,000 output tokens (API only)


MODELS: list[ModelSpec] = [
    ModelSpec(
        key="gptoss120b",
        kind="groq",
        model_id="openai/gpt-oss-120b",
        role="top_api",
        input_price_per_mtok=0.15,
        output_price_per_mtok=0.60,
    ),
    ModelSpec(
        key="gptoss20b",
        kind="groq",
        model_id="openai/gpt-oss-20b",
        role="cheap_api",
        input_price_per_mtok=0.075,
        output_price_per_mtok=0.30,
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

# Kept for reference / in case you want to swap a model back in later —
# src/models.py still has call_claude() and call_gemini() implemented,
# just unused by default.
# ANTHROPIC_ALTERNATIVES = [
#     ModelSpec(key="opus5", kind="anthropic", model_id="claude-opus-5",
#                role="top_api", input_price_per_mtok=5.00, output_price_per_mtok=25.00),
#     ModelSpec(key="haiku45", kind="anthropic", model_id="claude-haiku-4-5",
#                role="cheap_api", input_price_per_mtok=1.00, output_price_per_mtok=5.00),
# ]
# GOOGLE_ALTERNATIVES = [
#     ModelSpec(key="gemini38flash", kind="google", model_id="gemini-3.8-flash",
#                role="top_api", input_price_per_mtok=0.75, output_price_per_mtok=3.75),
#     ModelSpec(key="gemini35flashlite", kind="google", model_id="gemini-3.5-flash-lite",
#                role="cheap_api", input_price_per_mtok=0.30, output_price_per_mtok=2.50),
# ]

MODEL_BY_KEY = {m.key: m for m in MODELS}

# Hard cap requested by the brief so a bad prompt can't runaway-generate.
MAX_OUTPUT_TOKENS = 512

# Ollama's local HTTP server (default install).
OLLAMA_BASE_URL = "http://localhost:11434"

DB_PATH = "db/store.db"
ITEMS_PATH = "data/items.jsonl"
RESULTS_DIR = "results"
