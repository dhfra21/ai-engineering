# Project 0 — Bake-Off: Text-to-SQL

CS496 AI Engineering, Fall 2026. One-week project (see `../project0-bakeoff.pdf`
for the assignment brief). Compares a top API model, a cheap API model, and
a self-hosted open-weights model on one-shot text-to-SQL generation, scored
by execution accuracy against a small seeded database.

## Task

Given a natural-language question and a fixed schema, generate a single
SQLite `SELECT` statement. Correctness is checked by running the model's
SQL and the gold SQL against the same database and comparing result sets
(order-insensitive, floats rounded to 2 decimal places). No LLM judge, no
human in the scoring loop — see `src/db_utils.py::rows_match`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # then fill in GROQ_API_KEY
python db/build_db.py         # builds db/store.db (deterministic, seed=42)
python data/make_items.py     # regenerates + verifies data/items.jsonl (optional — already committed)
```

The two API-tier models run on [Groq](https://console.groq.com), which has
a free tier for both — get a key at [console.groq.com/keys](https://console.groq.com/keys)
(no credit card required; free-tier limits: 30 requests/minute, 1,000/day
per model). No API cost is incurred running this eval under the free
tier; `results/cost_summary.csv` still reports the published *paid* list
price, per the brief ("token counts x the list price"), which is also
what makes the "cost at 100x traffic" projection meaningful — see
`src/config.py` for the rates and the date they were checked.

For the open-weights model, install [Ollama](https://ollama.com) and pull
the model once:

```bash
ollama pull qwen2.5-coder:7b-instruct
ollama serve                  # if not already running as a background service
```

## Run

```bash
python -m src.run             # calls all 3 models on all 50 items -> results/per_item.csv
python -m src.score           # scores per_item.csv -> results/summary.csv, prints wrong answers
python -m src.cost            # fill results/hardware.json first -> results/cost_summary.csv
```

Run a single model while debugging: `python -m src.run --only gptoss120b`.

## Results

Run date: **2026-09-23**. All 50 items, one call per item, temperature 0,
`max_tokens=512`, same prompt byte-for-byte across all three models
(`src/prompt.py`). No call errors on any model.

| Model | Role | Accuracy | Easy | Medium | Hard | p50 latency | p95 latency | Cost / 1k requests (list price) |
|---|---|---|---|---|---|---|---|---|
| `openai/gpt-oss-120b` (Groq) | top API | **50/50 (100%)** | 15/15 | 19/19 | 16/16 | 972 ms | 5,445 ms | $0.136 |
| `openai/gpt-oss-20b` (Groq) | cheap API | 48/50 (96%) | 15/15 | 18/19 | 15/16 | 1,055 ms | 7,443 ms | $0.086 |
| `qwen2.5-coder:7b-instruct` | open-weights (self-hosted) | 47/50 (94%) | 15/15 | 18/19 | 14/16 | 14,136 ms | 25,152 ms | $0.057 † |

† The self-hosted figure is electricity-only at **100% utilisation** — it
assumes the laptop runs requests back-to-back, which at a 14.2 s average
is ~253 requests/hour. It is not "cheaper than the API at any volume":
the $0.0144/hour hardware cost is fixed whether the box is busy or idle,
so below ~106 requests/hour (vs the 120B) or ~167 requests/hour (vs the
20B) the API is cheaper per request. Self-hosting only wins inside the
106–253 req/hour window; above ~253 the laptop simply cannot keep up.
See `results/hardware.json` for the cost assumption, which excludes
hardware amortisation.

### What the 5 misses look like

All three models handled every *easy* item. The failures cluster on two
things, and only one of them is really about SQL ability:

- **Unrequested `WHERE status = 'completed'` filters — 3 of the 5 misses.**
  `gptoss20b` item 26 and `qwen7b` items 31 and 46 each produced
  well-formed SQL that answered a slightly narrower question than the one
  asked. This is the dominant failure mode, and it is a prompt/spec
  ambiguity as much as a model error.
- **`qwen7b` item 50** is a genuine aggregation error: it returned
  `SUM(quantity * unit_price)` over all completed orders where the
  question asked for the *average per order*, missing the required
  `GROUP BY order_id` subquery.
- **`gptoss20b` item 45 returned an empty string** and was scored wrong
  ("not a single read-only SELECT"). It is not a SQL failure: the
  response hit the 512-token cap (`output_tokens = 512`) with reasoning
  tokens before emitting any answer content. GPT-OSS models bill
  reasoning against the same budget, and the 20B reasons more verbosely
  than the 120B (205 vs 144 average output tokens). A higher
  `MAX_OUTPUT_TOKENS` would likely recover this item — worth noting as a
  harness limitation rather than a capability gap.

### Note on determinism

Temperature 0 did not give byte-identical output across runs. Re-running
the two Groq models produced different SQL on 14/50 (120B) and 8/50 (20B)
items versus the previous day's run, with no accuracy change. Expected
for batched MoE serving, but it means single-run accuracy differences of
1–2 items should not be read as meaningful separation between models.

**Which model would we choose, and when would we change?** At this
task's volume we would ship **`openai/gpt-oss-120b` on Groq**: it was
perfect on all 50 items, its p50 latency (972 ms) is the lowest of the
three, and at $0.136 per 1,000 requests the cost is negligible — the
accuracy gap over the cheap model costs about five cents per thousand
queries, which is not a trade worth making for a user-facing feature.
Three things would flip that. **Volume:** sustained traffic in the
106–253 requests/hour band makes the self-hosted 7B cheaper per request,
though the 14 s p50 rules it out for anything interactive. **Privacy:**
if schemas or questions could not leave our infrastructure, `qwen7b`
becomes the only option, and 94% accuracy for zero marginal cost is a
genuinely good showing for a 7B running partly on CPU. **Latency
budget:** none of the three is fast enough for a sub-500 ms
interaction — that would need a smaller model, caching, or dropping the
one-call-per-question design.

## Repo layout

```
db/       schema.sql, build_db.py (deterministic seed data), store.db (generated, gitignored)
data/     items.jsonl (50 questions + gold SQL), make_items.py (generator+verifier), LABELLING.md
src/      config.py, prompt.py, db_utils.py, models.py, run.py, score.py, cost.py
results/  per_item.csv, summary.csv, cost_summary.csv (generated), hardware.json, HARDWARE.md
report/   REPORT_OUTLINE.md (turn into report.pdf, 2 pages)
postmortem.md
```

## Contributions

_One entry per team member — fill in before freezing the repo._

- _Name — what they did_

## No API keys in this repo

`.env` is git-ignored. `GROQ_API_KEY` is read from the environment by
`src/run.py` (via `python-dotenv`), never hardcoded.
