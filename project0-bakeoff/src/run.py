"""Run all 50 items against all three models, one model fully before the
next, calls made one after another (not concurrently) so latency numbers
mean what the brief asks them to mean. Writes results/per_item.csv.

Usage:
    python -m src.run                       # all three models
    python -m src.run --only gptoss120b     # just one, e.g. while debugging

Requires:
    - db/store.db built (python db/build_db.py)
    - data/items.jsonl generated (python data/make_items.py)
    - GROQ_API_KEY set (for gptoss120b / gptoss20b), free at
      console.groq.com/keys — see .env.example
    - `ollama serve` running locally with the open-weights model pulled
      (for qwen7b) — see README.md
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

from src.config import MODELS, RESULTS_DIR  # noqa: E402
from src.models import call_claude, call_gemini, call_groq, call_ollama  # noqa: E402

load_dotenv()  # picks up GROQ_API_KEY (and GEMINI_API_KEY / ANTHROPIC_API_KEY, if used) from a local .env

ITEMS_PATH = Path(__file__).parent.parent / "data" / "items.jsonl"
OUT_PATH = Path(__file__).parent.parent / RESULTS_DIR / "per_item.csv"

FIELDNAMES = [
    "model_key", "model_id", "role", "item_id", "difficulty", "question",
    "raw_output", "latency_ms", "input_tokens", "output_tokens",
    "tokens_per_second", "call_error",
]


def load_items() -> list[dict]:
    items = []
    with ITEMS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def run_model(spec, items: list[dict], groq_client=None, anthropic_client=None, google_client=None) -> list[dict]:
    rows = []
    for i, item in enumerate(items, start=1):
        if spec.kind == "groq":
            result = call_groq(spec, item["question"], groq_client)
        elif spec.kind == "google":
            result = call_gemini(spec, item["question"], google_client)
        elif spec.kind == "anthropic":
            result = call_claude(spec, item["question"], anthropic_client)
        elif spec.kind == "ollama":
            result = call_ollama(spec, item["question"])
        else:
            raise ValueError(f"unknown model kind: {spec.kind}")

        print(f"[{spec.key}] {i}/{len(items)} item {item['id']} "
              f"({item['difficulty']}) — {result['latency_ms']:.0f} ms" if result["latency_ms"]
              else f"[{spec.key}] {i}/{len(items)} item {item['id']} — ERROR: {result['error']}")

        rows.append({
            "model_key": spec.key,
            "model_id": spec.model_id,
            "role": spec.role,
            "item_id": item["id"],
            "difficulty": item["difficulty"],
            "question": item["question"],
            "raw_output": result["raw_output"],
            "latency_ms": result["latency_ms"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "tokens_per_second": result["tokens_per_second"],
            "call_error": result["error"] or "",
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="run a single model key (e.g. gptoss120b, gptoss20b, qwen7b)")
    args = parser.parse_args()

    items = load_items()
    assert len(items) == 50, f"expected 50 items, found {len(items)} — regenerate data/items.jsonl"

    models_to_run = [m for m in MODELS if args.only is None or m.key == args.only]
    if not models_to_run:
        raise SystemExit(f"no model matches --only {args.only!r}")

    groq_client = None
    if any(m.kind == "groq" for m in models_to_run):
        from groq import Groq
        # Bump retries above the SDK default (2) — the free tier's request
        # cap means a burst of 429s is expected, not exceptional, and the
        # client already honors the server's Retry-After header per retry.
        groq_client = Groq(max_retries=5)  # reads GROQ_API_KEY from env

    anthropic_client = None
    if any(m.kind == "anthropic" for m in models_to_run):
        import anthropic
        anthropic_client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    google_client = None
    if any(m.kind == "google" for m in models_to_run):
        from google import genai
        google_client = genai.Client()  # reads GEMINI_API_KEY from env

    all_rows: list[dict] = []
    # Preserve prior results for models we didn't re-run this invocation.
    if OUT_PATH.exists():
        with OUT_PATH.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["model_key"] not in {m.key for m in models_to_run}:
                    all_rows.append(row)

    for spec in models_to_run:
        print(f"\n=== Running {spec.key} ({spec.model_id}) — {len(items)} items ===")
        all_rows.extend(run_model(spec, items, groq_client, anthropic_client, google_client))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} rows to {OUT_PATH}")
    print("Next: python -m src.score")


if __name__ == "__main__":
    main()
