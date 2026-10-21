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
- a 161-item golden set, labelled independently by two Claude instances (instructor-approved)
  from a written guide; the 4 disagreements and 1 agreed-but-wrong item were
  decided by Claude at the team's request (`data/labels/adjudication.jsonl`, `overrides.jsonl`)
- a harness that grades every item, not just the overall score
- an LLM judge with a reliability report and position/verbosity bias checks
- versioned prompts whose changelog ties every change to a score

## Setup (one command)

```bash
cp .env.example .env && python db/build_db.py && python data/make_queries.py
```

Then put the OpenAI key in `.env` (`OPENAI_API_KEY=...`).
You need Python 3.10+ and **nothing to install**: the harness uses only the
standard library and calls OpenAI's HTTP API directly.

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
| 2. Generate one blind candidate per query (baseline / weak model / planted error) | `python -m harness.candidates` | 161 × 20b, ~105 × qwen27b, ~56 × 120b |
| 3. **Two AI labellers label independently** from the full [guide](data/LABELLING_GUIDE.md) (instructor-approved in place of two humans): two separate Claude Code subagents, each given a blind packet | `python -m harness.claude_label export` → agent → `python -m harness.claude_label import` | 0 Groq calls. Optional extra raters on Groq: `python -m harness.ai_label` (~3k tokens per item) |
| 4. Agreement between labellers; adjudicate the disagreements (and any agreed-but-wrong items in `overrides.jsonl`); golden set | `python -m harness.golden --a claude-a --b claude-b` | 0 |
| 5. Judge vs humans (tune on dev, report on test) | `python -m harness.judge_eval --split dev` | 1 × 120b per item |
| 6. Position bias | `python -m harness.bias position --split test` | 2 × 120b per item |
| 7. Verbosity bias | `python -m harness.bias verbosity --split test --pad template` (and `--pad llm`) | ~3 × 120b per item |
| 8. Improve the system prompt on dev, logging each change | `python -m harness.run --split dev --system v2` → [CHANGELOG](prompts/CHANGELOG.md) | 60 × 20b + 60 × 120b |
| 9. Final test score and cost model | `python -m harness.run --split test --system vN` then `python -m harness.cost` | 101 + 101 |

Every successful response is cached in `.cache/llm/`. If you hit the daily
limit, the command stops cleanly; run it again the next day and it picks up
where it left off without spending quota twice.

## Models

| Role | Model (OpenAI) | Why |
|---|---|---|
| System under test | `gpt-5-nano` (low reasoning) | cheapest tier |
| Judge | `gpt-5-mini` (medium reasoning) | stronger model grading a weaker one |
| Second-model candidates (labelling only) | `gpt-4o-mini` | a different, older model's wording, with more natural errors |
| Planting errors (labelling only) | `gpt-5-mini` | |
| Labellers A and B | Claude Opus 5.5, two separate Claude Code subagents | a different model family from the judge and the system, so judge-vs-label agreement isn't self-agreement and no labeller grades its own answers |

All model ids and prices live in [`harness/config.py`](harness/config.py).
Prices are OpenAI's standard list rates.

## Results

Final configuration: system **v3** on `gpt-5-nano`, judge **v1** on `gpt-5-mini`
(OpenAI, since 2026-10-20). Counts and percentages; 95% CIs are Wilson intervals.

| What | Number | Source |
|---|---|---|
| Labeller agreement (raw, before adjudication) | 157/161 (97.5%), κ = 0.947 — two Claude instances, so an upper bound | `results/labels/agreement.md` |
| Items dropped / adjudicated / overridden | 0 / 4 / 17 (each override cites a guide rule) | same |
| Golden set | 161: 82 good, 79 bad (dev 60: 24 good / 36 bad; test 101: 58 good / 43 bad) | `data/golden.jsonl` |
| Judge vs human, golden **dev** | 54/60 (90.0%), κ = 0.79, bad caught 34/36, precision 34/38 | `results/judge/v1_gpt5mini_dev/summary.md` |
| Judge vs human, golden **test** | **65/101 (64.4%, CI 54.6–73.0%), κ = 0.33**, bad caught 40/43 (93.0%), precision 40/73 (54.8%); hard items 14/36 | `results/judge/v1_gpt5mini_test/summary.md` |
| Position bias: verdict flips when A/B swapped | 14/101 (13.9%), same slot both times 4/101; first slot won 61/202 (30.2%), second 63/202 (31.2%); picked the unbroken original in both orders 31/35 (88.6%) | `results/bias/v1_test/position.json` |
| Verbosity bias: judge-caught human-bad answers rescued by padding | template 2/40 (5.0%); llm 5/40 (12.5%, overstated: the pad model fixed 4 of them) | `results/bias/v1_test/verbosity-*.json` |
| System on dev: v1 → v3 | 43/60 and 40/60 (two runs) → 51/59 and 47/59 | `results/history.csv`, `prompts/CHANGELOG.md` |
| System on test, v3 (3 runs) | 78, 76, 80 of 101: mean 77.2%, range 75.2–79.2% | `results/history.csv` |
| Cost per 1k requests (system / + 10% judged) | $0.19 / $0.39; ~$5.90/month at 500 requests/day, ~$588 at 100× | `results/cost/20261021-101225_test_sys-v3_judge-v1.json` |

Read the test score together with the judge's test agreement: the judge fails
a third of human-good test answers, so 77% is a judge-graded number with fair
(κ 0.33) agreement with humans, not a direct measure of quality. See
`report/report.pdf` §4.

## Repo layout

```
db/        schema.sql, build_db.py         (copied from Project 0; store.db is generated)
data/      make_queries.py → queries.jsonl  161 SQL inputs + reference notes + split
           candidates.jsonl                 one blind candidate explanation per query
           labels/<name>.jsonl              raw labels per labeller; adjudication.jsonl
           golden.jsonl                     final golden set
           LABELLING_GUIDE.md
harness/   run.py (the one command), system.py, judge.py, llm.py (OpenAI client, cache,
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

From the commit history (git usernames). Replace with real names and add
anything that never showed up as a commit before freezing the repo.

- **dhfra21:** candidate generation; golden-set labelling, adjudication and guide v2–v3; judge v1/v2 and its evaluation; label fixes; switch from Groq to OpenAI; steps 6–9 on gpt-5-mini (bias checks, system prompts v2–v3, final test runs, cost model); README, postmortem and report.
- **OKmimech:** Project 1 scaffold (harness, judge, schemas, tests); step 6 position bias on Groq.

## No API keys in this repo

`.env` is git-ignored. `OPENAI_API_KEY` is read from the environment (or
`.env`) in `harness/llm.py` and is never hardcoded.
