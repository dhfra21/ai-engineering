# report.pdf outline (2 pages max)

Fill this in after running `src/run.py`, `src/score.py`, and `src/cost.py`
for real, then export to PDF (e.g. print-to-PDF from a Markdown preview,
or paste into a Word/Google Docs template). Delete this file's guidance
text before converting — it's scaffolding, not report content.

## 1. The task and one example item

One paragraph: text-to-SQL, one model call per question, scored by
execution accuracy against a seeded SQLite retail database (5 tables:
categories, customers, products, orders, order_items). Show one example
item verbatim from `data/items.jsonl` (question + gold_sql).

## 2. The data

- Where it came from: hand-written against `db/schema.sql`, not an
  external dataset (see `data/LABELLING.md` for the full method).
- How labels were checked: every gold query is executed against
  `db/store.db` before being written to `items.jsonl` — see
  `data/make_items.py`. A second read-through checked question/SQL
  intent match.
- Dev/test split: none — all 50 items are the test set, per the brief.

## 3. Setup

- 3 model names + exact IDs and the date you ran them (from
  `results/per_item.csv`'s `model_id` column).
- Settings: max output tokens, temperature 0 (all three models support it
  here — no deviation needed), single-call-per-item, no retrieval, no agent.
- Note both API-tier models come from Groq and are the same OpenAI
  GPT-OSS family at two sizes (see `postmortem.md` for why, and why we
  moved off Gemini's free tier), and that cost is computed at list price
  even though the free tier made actual spend $0.
- Prompt: reference `src/prompt.py` (same prompt, byte-for-byte, all 3 models).
- Hardware for the self-hosted model: `results/HARDWARE.md`.

## 4. Results table + 3 wrong answers per model

Paste the table from `results/summary.csv` (accuracy, n/50, breakdown by
difficulty) and the table from `results/cost_summary.csv` (p50/p95
latency, cost per 1k requests). Paste 3 wrong answers per model from the
`python -m src.score` console output.

## 5. Your choice, and when you would change it

One paragraph. Which model would you actually use for this kind of task,
and what conditions (traffic volume, latency budget, accuracy floor,
privacy/self-hosting requirement) would flip that choice?

## 6. Cost at 100x traffic and the break-even volume

Pull the `_at_100x` columns from `results/cost_summary.csv` and the
break-even requests/hour figure printed by `python -m src.cost`. State
the assumption plainly: API cost is flat per request regardless of
volume (no bulk discount modeled); self-hosted cost per request falls
until the box's real throughput ceiling, then goes flat too — say which
regime your traffic estimate falls into.
