# Project 3: The Operator

CS496 AI Engineering, Fall 2026. Brief: [`../project3-operator.pdf`](../project3-operator.pdf).

An **email-triage agent** that works in a **sandboxed mailbox**. Given an instruction ("label the billing mail, archive the
newsletters, draft a reply to DF") it lists and reads email, labels and archives it, drafts replies, and sends **only after a
human approves**. Email text is treated as untrusted (prompt injection). It is graded on its whole path, not just its answer.

## DF, start here (5 minutes)

**First read [`HANDOFF.md`](HANDOFF.md): where we are, why we stopped (the API keys ran out), and exactly what is left.**

1. **Read** [`report/report.pdf`](report/report.pdf) (3 pages): the whole project in one place.
2. **Run the tests**: they need no key and take a second. Setup below, then `.venv/bin/python -m pytest -q` (18 pass).
3. **Try the agent** (needs a key, see Setup): `.venv/bin/python -m agent.cli "archive the promo emails and draft a reply to DF"`.
   It asks `Approve? [y/N]` before any send. Try `"read email 5 and label it"` to see an injection attempt resisted (email 5 is the attacker).
4. **What is left for us** is in [`TASKS.md`](TASKS.md). The most useful job for you: run the pending eval below with **your own Groq key**.

### The one open item: re-run the injection scenarios

We rewrote 8 injection tasks so the agent *has to read* the malicious email (before, it often never opened it, so the attack
was never tested). The free Groq key we used hit its **200,000 tokens/day** limit before we could re-run them. With your key:

```bash
.venv/bin/python -m eval.run_eval --tag v3 --category injection     # about 40k tokens, a few minutes
```

Then copy the line "Injection exposure: the agent actually read the malicious body in X of 11; attacks that worked: Y" from
`results/eval_v3.md` into `threat_model.md` and `report/report.md` section 5 (rebuild the PDF: `.venv/bin/python report/build_pdf.py`).
A **full** run is `python -m eval.run_eval --tag v3` (41 scenarios, ~145k tokens, 30 to 60 min on the free tier): do not start two at once,
and one run per key per day is all the free limit allows.

## Setup (one command)

```bash
uv venv --python 3.12 .venv && uv pip install -p .venv/bin/python -r requirements.txt && cp .env.example .env
```

Then put a key in `.env` (**never commit it**; `.env` is gitignored). Pick one:

- **Groq, free** (what we used): `LLM_PROVIDER=groq` and `GROQ_API_KEY=...` from console.groq.com. Default model `openai/gpt-oss-120b`.
- **OpenAI**: `LLM_PROVIDER=openai` and `OPENAI_API_KEY=...`. The course key was out of credits when we tried it. Default model `gpt-4o-mini`.

The format is `NAME=value` with no spaces and no quotes.

## What needs a key and what does not

| needs a key | needs no key |
|---|---|
| `python -m agent.cli "..."` (the live agent, the demo) | `pytest -q` (18 tests, scripted fake model) |
| `python -m eval.run_eval` (the real eval) | `python -m sandbox.mailbox` (reset the mailbox) |
| | `python -m eval.build_scenarios`, `python -m eval.cost_model`, `python report/build_pdf.py` |

## Results (run `v2`, 41 scenarios, `openai/gpt-oss-120b`; full tables in `results/eval_v2.md`)

| | n | success | safe |
|---|---|---|---|
| all | 41 | 100% | 100% |
| label / draft / send / multi | 24 | 100% | 100% |
| tool failure (recovery after failure) | 6 | 100% | 100% |
| injection | 11 | 100% | 100% |

About $0.0007 and 3 steps per task; $21/month at 100x. **Read the caveats** in the report: the model read the malicious email in only
3 of the 11 injection runs (the re-run above fixes that), the scenarios are ours so the eval is likely easier than a live audience,
and it is one run of one model. The first baseline (37 scenarios, `results/eval_baseline.md`) scored 97%.

## How it fits together

```
task -> agent/loop.py -> model picks a tool -> agent/tools.py -> sandbox/mailbox.py (SQLite)
              ^                                      |
              └────── result text or "error: ..." ───┘
 stops when: the model answers | 12 steps | $0.05 | same call and result 3 times
```

- `agent/`: `tools.py` (5 tools, schemas, safe writes), `loop.py` (the loop and the stop rule), `config.py` (limits, providers, prices), `cli.py`
- `sandbox/`: `mailbox.py` and `seed.json` (12 fake emails, one is an injection)
- `eval/`: `build_scenarios.py` (edit scenarios here, it writes `scenarios.jsonl`), `run_eval.py` (the grader), `cost_model.py`
- `tests/`: no-key tests for tools, the stop rule, the eval grader
- `design.md` (why it is built this way), `errors.md` (14 failure kinds, each with a test), `threat_model.md`, `postmortem.md`, `TASKS.md`, `results/`

## Contributions

*To fill in before handing in: what OK did, what DF did.*
