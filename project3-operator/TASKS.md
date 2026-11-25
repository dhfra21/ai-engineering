# Project 3: work split (17 Nov 2026)

Deadline: repo frozen before the first session of Week 13. **Instructor OK on the idea is due end of Week 11.**
Full status and why we stopped: see [`HANDOFF.md`](HANDOFF.md).
Keys: a Groq key (free) or the course OpenAI key in your own `project3-operator/.env` (never commit it). Only the eval and the live agent need one.

| Task | Owner | Status |
|---|---|---|
| Send the instructor the idea (email inbox triage) and get the OK | OK + DF | **Done**: approved (confirmed 25 Nov) |
| Sandbox, 5 tools, loop, stop rule + tests | OK | **Done** (18 tests, `pytest -q`) |
| Run the agent for real, tune the prompt | OK | **Done** (Groq `gpt-oss-120b`) |
| 30+ scenarios with expected end states | OK | **Done**: 41 (`eval/build_scenarios.py`) |
| Trajectory eval: step accuracy, precision, wasted steps, success, safety | OK | **Done**, `results/eval_v2.md` (100%), first baseline 97% |
| Failure injection and recovery-after-failure rate | OK | **Done**: 6 scenarios, 6/6 |
| 5+ injection scenarios and results | OK | **Done**: 11, results in `threat_model.md` |
| Re-run the 8 reworded injection scenarios | DF | **Done 24 Nov** (`eval_v3`, `eval_v4`): 1 of 11 attacks still works, written up |
| Cost model | OK | **Done**, `results/cost_model.md`. Re-check list prices before quoting |
| `errors.md` with a test per class | OK | **Done**: 14 classes (the "user changes mind" one is stated as not covered) |
| Report (max 4 pages) | OK + DF | **Done**: `report/report.pdf`, 1 page, updated with `v6` on 25 Nov |
| `postmortem.md` | OK | **Done**. Add anything the re-run teaches |
| Clean-clone check | OK + DF | **Done on 17 Nov** (OK, 18 tests) and **again 25 Nov** (DF, Windows): fresh clone of `08d373b`, new venv, no keys, 21 tests pass |
| README Contributions section | OK + DF | **Done 25 Nov** (OK to confirm the 24 Nov credit moved to the OK line) |
| Optional: more or harder scenarios, a second model, a second full run to show variance | DF | nice to have: the eval is probably easier than a live audience |
| Rehearse the demo, including a live injection attempt | OK + DF | **Rehearsed 25 Nov (DF)**: use `"Read email 5 and give it the label you think fits."` (the old "read email 5 and label it" made the agent ask which label, 0 tool calls). Reset first: `python -m sandbox.mailbox` |

## Update 24 Nov (OK, end of day): what DF still has to do with his own key
- Added the scope guard (`agent/loop.py`, `tests/test_scope_guard.py`, 21 tests) and ran `eval_v3`, `v4`, `v5` (injection only). See `HANDOFF.md`.
- **Open:** (1) a **full 41-scenario run** (`--tag v6`) on the new prompt + guard: only the injection category was re-run, the others were last measured on the old prompt; put the numbers in the report table. (2) Send/confirm the **instructor OK**. (3) Confirm the README **Contributions** lines. (4) **Demo rehearsal** with a working key. (5) Rebuild the PDF if numbers change and run the **clean-clone check**.

## Update 25 Nov (DF)
- **Instructor OK: received.** The idea (email inbox triage) is approved.
- **Full run `v6` done** (41 scenarios, guard + hardened prompt): 98% success, 100% safe, 0 of 11 attacks worked (11 of 11 exposed, guard never fired). s08 failed again (regression, written up). Report, `threat_model.md`, `postmortem.md`, `cost_model.md` and the PDF updated.
- Fixed Windows-only bugs (SQLite file locking, cp1252 encoding, Chrome path in `build_pdf.py`).
- README **Contributions** filled in; **clean-clone check** passed after the push (fresh clone of `08d373b`, no keys, 21 tests). All DF handoff items are done.
