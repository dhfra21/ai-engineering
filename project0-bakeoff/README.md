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
cp .env.example .env          # then fill in ANTHROPIC_API_KEY
python db/build_db.py         # builds db/store.db (deterministic, seed=42)
python data/make_items.py     # regenerates + verifies data/items.jsonl (optional — already committed)
```

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

Run a single model while debugging: `python -m src.run --only opus5`.

## Results

_Populate after running the commands above — paste the console output of
`python -m src.score` and `python -m src.cost`, or the CSVs' contents._

| Model | Role | Accuracy | Easy | Medium | Hard | p50 latency | p95 latency | Cost / 1k requests |
|---|---|---|---|---|---|---|---|---|
| `claude-opus-5` | top API | _/50 | _/15 | _/19 | _/16 | _ ms | _ ms | $_ |
| `claude-haiku-4-5` | cheap API | _/50 | _/15 | _/19 | _/16 | _ ms | _ ms | $_ |
| `qwen2.5-coder:7b-instruct` | open-weights (self-hosted) | _/50 | _/15 | _/19 | _/16 | _ ms | _ ms | $_ |

**Which model would we choose, and when would we change?** _One paragraph
— see `report/REPORT_OUTLINE.md` section 5 for the full version that
belongs in `report.pdf`._

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

`.env` is git-ignored. `ANTHROPIC_API_KEY` is read from the environment
by `src/run.py` (via `python-dotenv`), never hardcoded.
