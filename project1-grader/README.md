# Project 1 — The Grader: explaining SQL in plain words

CS496 AI Engineering, Fall 2026, Weeks 2–4. The brief is in
[`../project1-grader.pdf`](../project1-grader.pdf).

**Task.** The system gets a SQLite query and explains in plain words what it
returns, for a reader who doesn't know SQL. There's no single correct
explanation: many wordings are right, and a fluent one can still be wrong.
Typical errors are misreading a `LEFT JOIN`, dropping the `LIMIT`, or
confusing a count of rows with a count of distinct values. Exact match
can't grade that, but a careful person can, using a two-page guide. The
queries run on the same retail database as Project 0, so every claim can be
checked against real results.

**What's in here:**
- a 161-item golden set, labelled by two people with a written guide
- a harness that grades every item, not just the overall score
- an LLM judge with a reliability report and position/verbosity bias checks
- versioned prompts whose changelog ties every change to a score

## Setup (one command)

```bash
cp .env.example .env && python db/build_db.py && python data/make_queries.py
```

Then put your Groq key in `.env` ([free, no card](https://console.groq.com/keys)).
You need Python 3.10+ and **nothing to install**: the harness uses only the
standard library and calls Groq's HTTP API directly.

To try everything offline with fake, hash-based answers, add
`GRADER_BACKEND=mock` in front of any command. Mock output goes to
`results/mock/`, which is git-ignored and never mixed with real results.

## Run (one command)

```bash
python -m harness.run --split test --system v1
```

This runs the system on every test query, has the judge grade every answer,
and writes `results/runs/<run_id>/per_item.jsonl` with one row per item:
input, output, score, reason, failed criteria, tokens, latency, cost and any
error. It also writes `summary.json` and appends a line to
`results/history.csv`.

Tests: `python -m unittest discover -s tests -t .` (includes an end-to-end
run on the mock backend).

## The whole workflow

| Step | Command | Model calls (free tier: ~1,000/day/model) |
|---|---|---|
| 1. Build the 161 queries (verified against the DB, dev/test split fixed) | `python data/make_queries.py` | 0 |
| 2. Generate one blind candidate per query (baseline / weak model / planted error) | `python -m harness.candidates` | 161 × 20b, ~105 × 8b, ~56 × 120b |
| 3. **Two people label independently** ([guide](data/LABELLING_GUIDE.md)) | `python -m harness.label --labeller <name>` | 0 |
| 4. Agreement between labellers, adjudication, golden set | `python -m harness.golden --a <name> --b <name>` | 0 |
| 5. Judge vs humans (tune on dev, report on test) | `python -m harness.judge_eval --split dev` | 1 × 120b per item |
| 6. Position bias | `python -m harness.bias position --split test` | 2 × 120b per item |
| 7. Verbosity bias | `python -m harness.bias verbosity --split test --pad template` (and `--pad llm`) | ~3 × 120b per item |
| 8. Improve the system prompt on dev, logging each change | `python -m harness.run --split dev --system v2` → [CHANGELOG](prompts/CHANGELOG.md) | 60 × 20b + 60 × 120b |
| 9. Final test score and cost model | `python -m harness.run --split test --system vN` then `python -m harness.cost` | 101 + 101 |

Every successful response is cached in `.cache/llm/`. If you hit the daily
limit, the command stops cleanly; run it again the next day and it picks up
where it left off without spending quota twice.

## Models

| Role | Model (Groq) | Why |
|---|---|---|
| System under test | `openai/gpt-oss-20b` | cheap tier from Project 0 |
| Judge | `openai/gpt-oss-120b` | stronger model grading a weaker one |
| Weak candidates (labelling only) | `llama-3.1-8b-instant` | produces realistic mistakes |
| Planting errors (labelling only) | `openai/gpt-oss-120b` | |

All model ids and prices live in [`harness/config.py`](harness/config.py).
Prices are Groq's paid list rate (the free tier costs $0), so the cost model
also holds for traffic past the free tier.

## Results

_Fill these in from the files named in each row. Report counts and
percentages, never a single number on its own._

| What | Number | Source |
|---|---|---|
| Labeller agreement (raw, before adjudication) | _/_ (_%), κ = _ | `results/labels/agreement.md` |
| Items dropped / adjudicated | _ / _ | same |
| Judge vs human, golden **test** | _/_ (_%), κ = _, bad caught _/_ | `results/judge/<v>_gptoss120b_test/summary.md` |
| Position bias: verdict flips when A/B swapped | _/_ (_%) | `results/bias/<v>_test/position.json` |
| Verbosity bias: human-bad answers rescued by padding | template _/_, llm _/_ | `results/bias/<v>_test/verbosity-*.json` |
| System on test: v1 → final | _/101 → _/101 | `results/history.csv` |
| Cost per 1k requests (system / + 10% judged) | $_ / $_ | `results/cost/<run_id>.json` |

## Repo layout

```
db/        schema.sql, build_db.py         (copied from Project 0; store.db is generated)
data/      make_queries.py → queries.jsonl  161 SQL inputs + reference notes + split
           candidates.jsonl                 one blind candidate explanation per query
           labels/<name>.jsonl              raw labels per labeller; adjudication.jsonl
           golden.jsonl                     final golden set
           LABELLING_GUIDE.md
harness/   run.py (the one command), system.py, judge.py, llm.py (Groq client, cache,
           structured output), schemas.py (fixed JSON schemas), prompts.py,
           candidates.py, label.py, golden.py, judge_eval.py, bias.py, cost.py, stats.py
prompts/   system/, judge/, judge_pairwise/, perturb/, pad/  — <version>.md each
           CHANGELOG.md
results/   runs/<run_id>/, history.csv, labels/, judge/, bias/, cost/
report/    REPORT_OUTLINE.md  → report.pdf (max 4 pages)
tests/     unit tests + mock end-to-end test
postmortem.md
```

## Contributions

_One entry per team member. Fill this in before freezing the repo._

- _Name: what they did_

## No API keys in this repo

`.env` is git-ignored. `GROQ_API_KEY` is read from the environment (or
`.env`) in `harness/llm.py` and is never hardcoded.
