# Project 3: work split (17 Nov 2026)

Deadline: repo frozen before the first session of Week 13. **Instructor OK on the idea is due end of Week 11.**
Full status and why we stopped: see [`HANDOFF.md`](HANDOFF.md).
Keys: a Groq key (free) or the course OpenAI key in your own `project3-operator/.env` (never commit it). Only the eval and the live agent need one.

| Task | Owner | Status |
|---|---|---|
| Send the instructor the idea (email inbox triage) and get the OK | **OK or DF: do first** | not done |
| Sandbox, 5 tools, loop, stop rule + tests | OK | **Done** (18 tests, `pytest -q`) |
| Run the agent for real, tune the prompt | OK | **Done** (Groq `gpt-oss-120b`) |
| 30+ scenarios with expected end states | OK | **Done**: 41 (`eval/build_scenarios.py`) |
| Trajectory eval: step accuracy, precision, wasted steps, success, safety | OK | **Done**, `results/eval_v2.md` (100%), first baseline 97% |
| Failure injection and recovery-after-failure rate | OK | **Done**: 6 scenarios, 6/6 |
| 5+ injection scenarios and results | OK | **Done**: 11, results in `threat_model.md` |
| **Re-run the 8 reworded injection scenarios** (`--category injection`) and update `threat_model.md` + report section 5 | **DF** (own Groq key) | **open**, see README. Our key hit its daily token limit |
| Cost model | OK | **Done**, `results/cost_model.md`. Re-check list prices before quoting |
| `errors.md` with a test per class | OK | **Done**: 14 classes (the "user changes mind" one is stated as not covered) |
| Report (max 4 pages) | OK | **Done**: `report/report.pdf`, 3 pages. Update after the injection re-run |
| `postmortem.md` | OK | **Done**. Add anything the re-run teaches |
| Clean-clone check | OK | **Done on 17 Nov** (fresh venv, 18 tests pass, no keys). Run again after the last push |
| README Contributions section | **OK + DF** | **open**: write who did what |
| Optional: more or harder scenarios, a second model, a second full run to show variance | DF | nice to have: the eval is probably easier than a live audience |
| Rehearse the demo, including a live injection attempt (`agent.cli "read email 5 and label it"`) | OK + DF | not done. Both need a working key on the demo machine |
