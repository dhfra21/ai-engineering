# UPDATE 24 Nov (read first): the pending re-run is DONE, new work for DF

- Injection re-run done (`results/eval_v3.md`, `v4`, `v5`): once the agent was forced to read the malicious email, **attacks did work** (v3: s31, v4: s40). Fixes: hardened prompt + a **code guard** (writes limited to the emails the user named) + loop retry on malformed tool calls. `v5`: 0 of 11, but the guard never fired, so be honest that results vary between runs.
- Tests: 21 pass (`pytest -q`). Report is now 1 page (`report/report_long.md` is the old 3-page version).
- **What is left for you (needs your own Groq key; ours is out of daily tokens):**
  1. Full run: `.venv/bin/python -m eval.run_eval --tag v6` (~145k tokens, one per key per day, use `--resume` after a rate-limit error). Update the report table and `threat_model.md`; rebuild the PDF (`python report/build_pdf.py`, needs `markdown` and Chrome).
  2. Instructor OK for the idea: confirm it was sent, update `TASKS.md`.
  3. Confirm the README **Contributions** section (DF line says "to confirm").
  4. Demo rehearsal (the brief says the demo includes an injection attempt): `python -m agent.cli "read email 5 and label it"`. Note the guard only covers requests that name email ids.
  5. Clean-clone check after the final push.
- The older text below is from 17 Nov; where it says the re-run is pending, it is out of date.

# Handoff to DF: where we are (17 Nov 2026, evening)

Written by OK so you can pick this up without asking. Read this first, then `report/report.pdf` (3 pages).

## One-paragraph summary

The agent, sandbox, tools, stop rule, eval (41 scenarios), cost model, report, postmortem, error taxonomy and threat model
are **built and written**. The eval result we trust is run `v2`: 100% success and 100% safe on 41 scenarios. **One thing is
unfinished** because our API key ran out of daily quota: re-running the injection scenarios we reworded (details below).
Nothing else is blocked.

## Why we stopped: the API key situation

| Key | Status |
|---|---|
| Course **OpenAI** key | **Dead**: `credit_balance_exhausted` (no credits). We could not use it at all. Ask the professor for a new one if you want to use OpenAI |
| **Groq** key (free, OK's) | **Daily token limit used up** for model `openai/gpt-oss-120b`: 200,000 tokens/day, all spent by 17 Nov evening. Other limits: 8,000 tokens/minute, 1,000 requests/day |

- One full eval run (41 scenarios) is about **145k tokens**, so a free Groq key gives roughly **one full run per day**.
- The limit is rolling, so OK's key recovers gradually (the error message says how many minutes until it does) and fully within 24 h.
- **Use your own Groq key** (free, 2 minutes at console.groq.com) so you have a fresh 200k. Put it in your own `.env`.
- Never commit a key. `.env` is gitignored. The Groq key OK used was pasted in a chat: OK should regenerate it.

## What is done (all in this folder)

| Part | File | State |
|---|---|---|
| 5 tools, schemas, idempotent writes | `agent/tools.py` | done, tested |
| Loop and stop rule (12 steps, $0.05, 3 identical call+result) | `agent/loop.py`, `agent/config.py` | done, tested |
| Sandbox (fake SQLite mailbox, 12 emails) | `sandbox/` | done |
| Human checkpoint before any send | `agent/tools.py`, `agent/cli.py` | done, tested |
| 41 scenarios | `eval/build_scenarios.py` -> `eval/scenarios.jsonl` | done |
| Eval runner (success, safe, step accuracy, precision, wasted, recovery, cost, time) | `eval/run_eval.py` | done |
| Results we trust | `results/eval_v2.md` (+ `.json`) | done: 41/41 |
| Earlier baseline (37 scenarios, old prompt) | `results/eval_baseline.md` | done: 97% (one real miss, s08) |
| Cost model | `results/cost_model.md` (`python -m eval.cost_model --tag v2`) | done |
| Error taxonomy (14 kinds, a test each) | `errors.md` | done |
| Threat model and 11 injection results | `threat_model.md` | done, **one caveat below** |
| Report, 3 pages | `report/report.md`, `report/report.pdf` | done, **update after the re-run** |
| Postmortem | `postmortem.md` | done |
| 18 tests, no key needed | `tests/` | pass; also pass on a fresh copy |

## What is NOT done

1. **Instructor OK on the idea (email inbox triage).** Due end of Week 11. Whoever sends it, write it in `TASKS.md`.
2. **Re-run the reworded injection scenarios** (the important one, below).
3. **README "Contributions" section**: blank on purpose. Write who did what.
4. **Demo rehearsal** for the first session of Week 13, including a live injection attempt (try `python -m agent.cli "read email 5 and label it"`). Needs a working key on the demo machine.
5. Nice to have: more and harder scenarios, a second model, a second full run to show variance.

## The open item in detail: why the injection re-run matters

In run `v2`, 0 of 11 injection scenarios caused damage. But reading the trajectories showed that in **8 of the 11 the agent
never opened the malicious email** (it labelled from the sender and subject), so the attack text never reached the model.
Only 3 were real tests (s30, s32, s33). After that we:

- reworded the 8 tasks to start with "Read email N, then ..." (in `eval/build_scenarios.py`; `scenarios.jsonl` is already rebuilt),
- added an `exposed` metric to `eval/run_eval.py` (did the agent read the malicious body?).

We could not run them: the key hit its daily limit. **To finish:**

```bash
cd project3-operator
uv venv --python 3.12 .venv && uv pip install -p .venv/bin/python -r requirements.txt && cp .env.example .env
# edit .env: LLM_PROVIDER=groq and GROQ_API_KEY=<your key>   (NAME=value, no spaces, no quotes)
.venv/bin/python -m pytest -q                                      # 18 should pass, needs no key
.venv/bin/python -m eval.run_eval --tag v3 --category injection    # about 40k tokens, a few minutes
```

Then:
1. Open `results/eval_v3.md`; find the line "Injection exposure: the agent actually read the malicious body in X of 11; attacks that worked among those: Y".
2. Put X and Y into `threat_model.md` (section "An important limit of this result") and `report/report.md` section 5, and replace the "re-run is pending" wording.
3. Rebuild the PDF: `.venv/bin/python report/build_pdf.py` (needs `markdown` installed and Google Chrome; `uv pip install markdown`).
4. If any attack **worked**, that is a real finding: report it honestly in the threat model and postmortem, and consider a fix (for example, wrap the subject line too, or add a rule in `agent/loop.py` SYSTEM). Do not hide it: "a postmortem with no problems loses points."

If the numbers differ from `v2` elsewhere, a full run is `python -m eval.run_eval --tag v3` (about 145k tokens: only with a fresh key, and do not start two runs at once).

## Gotchas we hit (so you do not)

- **`.env` format**: `OPENAI_API_KEY=sk-...`. A line like `OPENAI API KEY : sk-...` is silently ignored.
- **A 429 is not always a rate limit**: `credit_balance_exhausted` (OpenAI) and the daily token limit (Groq) will never succeed on retry. The loop now fails at once for a long wait and prints the reset time.
- **Groq model names**: `llama-3.3-70b-versatile` was not available on our account; `openai/gpt-oss-120b` was. List what your key has: `curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`.
- **Timing numbers in `v2` include rate-limit waits** (p50 13 s). New runs also record `api_seconds` (model time only).
- **Do not run two evals in parallel**: they share one token-per-minute limit and both slow down.
- `--resume` redoes only scenarios that errored; use it after a rate-limit failure instead of starting over.
- Prices in `eval/cost_model.py` are list prices from memory: check the pricing pages before quoting them.

## Honest weaknesses (already written in the report)

- The scenarios are ours and the model scores near 100%, so the eval is probably easier than a live audience.
- The s08 prompt fix was tuned on a scenario in the test set.
- One model, one run each; free-tier runs are noisy.
- "User changes their mind mid-task" is not covered (one instruction per run).
