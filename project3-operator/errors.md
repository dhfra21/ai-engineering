# Error taxonomy

Every kind of thing that can go wrong, what the agent does, and the test that shows it. "Unit test" runs without an API key
(`pytest -q`); "eval scenario" needs a model key (`python -m eval.run_eval`) and its measured result is in `results/eval_v3.md`.

| # | Kind | What the agent does | Test | 
|---|---|---|---|
| 1 | **Bad arguments** (wrong type, unknown key, bad enum value, too long) | The tool refuses with `error: ...` naming the problem; the model can fix and retry. Nothing is written | unit: `test_tools.py::test_bad_arguments_give_clear_errors` |
| 2 | **Unknown id / empty result** | `error: no email with id N. Call list_emails...` or `no emails in 'archive'`; nothing is changed | unit: `test_bad_arguments_give_clear_errors`, `test_loop.py::test_empty_folder_result_is_plain_text`; eval scenarios s09 (id 99) and s41 (empty folder) |
| 3 | **Malformed JSON from the model** | `error: arguments were not valid JSON` returned as the tool result; the loop continues | unit: `test_loop.py::test_bad_json_arguments_become_an_error_the_model_sees` |
| 4 | **Wrong tool** (a tool that does not exist, e.g. `delete_email`) | `error: unknown tool 'delete_email'. Available tools: ...`; nothing is deleted (there is no delete tool at all) | unit: `test_loop.py::test_wrong_tool_name_is_an_error_the_model_can_recover_from` |
| 5 | **Invalid choice** (label "urgent" is not allowed) | Rejected by the enum; the agent should change nothing or pick an allowed label | eval scenario s10 |
| 6 | **Tool down / timeout** (temporary) | The eval injects `error: service temporarily unavailable`; the agent retries and finishes | eval scenarios s25 to s28 (read, list, label, draft tools each fail once) |
| 7 | **Tool down for good** | The same call returns the same error 3 times, so the run is stopped as `stuck` with a message saying why; no collateral damage | unit: `test_early_stop_tells_the_user_why`; eval scenario s29 |
| 8 | **Loop / never finishes** | Cut off at `MAX_STEPS` (12) | unit: `test_never_stops_on_its_own_model_is_cut_off_at_max_steps` |
| 9 | **Same call repeated** | Stopped as `stuck` after 3 identical call+result pairs. A retry after an error is **not** stuck (the result differs once it works) | unit: `test_identical_repeats_are_detected_as_stuck`, `test_eval.py::test_failure_injection_then_recovery` |
| 10 | **Cost runaway** | Stopped at `MAX_COST_USD` ($0.05) | unit: `test_cost_budget_stops_the_run` |
| 11 | **Human refuses the send** | `refused: ...`; the draft stays saved, nothing is sent, the agent must not retry | unit: `test_send_needs_approval_and_is_idempotent`; eval scenario s16 |
| 12 | **Same write twice** (the model repeats itself) | Labels, drafts and sends are idempotent: the second call changes nothing | unit: `test_label_is_idempotent`, `test_draft_is_idempotent`, `test_send_needs_approval...` |
| 13 | **Agent says "done" but missed something** | Not prevented by code; caught only by the eval's end-state check | eval scenario s08 (the first baseline run failed it; see `postmortem.md` section 6) |
| 14 | **User changes their mind mid-task** | **Not covered.** The agent takes one instruction per run, so this is a stated limitation, not a tested behaviour | none |

**Recovery after failure** (the brief's metric): in the eval, the 6 `failure` scenarios inject a tool error; the rate at
which the task still ends correct is in `results/eval_v3.md` ("Recovery after failure").
