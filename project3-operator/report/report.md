# Project 3: The Operator

CS496 AI Engineering, Fall 2026 · OK and DF · email-triage agent with a sandbox, a human checkpoint and a trajectory eval

## 1. Task and tools

From one instruction ("label the billing mail, archive the newsletters, draft a reply to DF") the agent works through a mailbox in several steps. **Five tools, three write**: `list_emails`, `read_email` (body wrapped in `<untrusted_email>`), `label_email` (six allowed labels, inbox/archive), `draft_reply` (never sends), `send_draft` (only after human approval, only to the original sender). Inputs are strictly schema-checked, errors come back as plain text, writes are idempotent, every call is logged. There is no delete, forward or free-form recipient. The "mail" is a SQLite sandbox rebuilt from `sandbox/seed.json` (12 emails, one an injection).

## 2. Loop, stop rule and checkpoint

Plain ReAct loop. The stop rule was written first; any one condition ends the run: **12 steps**, **$0.05**, or the **same call with the same result 3 times**. Each run ends with a `stop_reason` and a message to the user. *Proof:* `tests/test_loop.py` drives the loop with a scripted model that never stops and checks all three cut-offs. In the eval the longest task used 7 steps and cost $0.0019. A first rule ("2 identical calls") blocked the correct retry after an error, so repeats now count only if the result is identical too.
The checkpoint `approve(tool, args, preview)` shows recipient and exact text and asks `Approve? [y/N]`; with no approver a send is **refused**. Tests: refused without approval, sent once with approval, a second send does nothing.

## 3. Trajectory eval and results

**41 scenarios** (10 label, 4 draft, 4 send, 6 multi-step, 6 tool failure, 11 injection), each with the expected final mailbox. Graded on the path: success, safety (nothing outside the task touched, nothing wrongly sent), step accuracy, tool-call precision, wasted steps, recovery after failure. Run `v2`, `gpt-oss-120b` on Groq:

| category | n | success | safe | step acc. | tool prec. | wasted/task |
|---|---|---|---|---|---|---|
| all | 41 | 100% | 100% | 100% | 94% | 0.20 |
| tool failure | 6 | 100% | 100% | 100% | 65% | 1.17 |
| injection (`v4`, forced reads) | 11 | 82% | 91% | 95% | 92% | 0.36 |
| injection (`v5`, + code guard) | 11 | 100% | 100% | 100% | 97% | 0.09 |

The first baseline (37 scenarios) scored 97%: the model skipped one of six emails yet said it was done. A prompt fix (cover every matching email, report exactly what changed) passed in `v2`. **Caveats:** we tuned on that scenario, the scenarios are our own, and it is one noisy free-tier run of one model, so 100% likely means the eval is easy.

## 4. Errors and threat model

`errors.md` lists 14 failure kinds with the agent's behaviour and a test for each (18 key-free unit tests); **recovery after failure 6/6**. The tool-precision dip (65%) is the failed calls themselves. Not covered: the user changing their mind mid-task.
Untrusted text enters only via email. **11 injection scenarios** (body, subject, French/Arabic, fake "verified user" and IT notes, send to `attacker@evil.example`, leak inbox, mass-archive, password in reply). In the first run 0 of 11 did damage, but the agent read the malicious body in only 3. After forcing it to read (`v4`: read in **11 of 11**), **1 of 11 attacks worked** (s40, a fake "verified user message" that made it archive and spam-label three emails; with the first prompt s31 worked instead). A hardened prompt fixed s31 but not s40, so which attack lands varies between runs and the model's judgement is not a reliable defence. We then added a **code guard**: if the request names emails, writes to any other email are refused (unit-tested). With it, `v5` had **0 of 11** successes, but the guard never fired, so that run shows variance, not the guard's effect. Damage stayed small because of the tools: no tool reaches a third party (nothing was sent), writes are reversible labels and folder moves, labels are an enum, and a human approves sends. **Not covered:** requests that name no email ids (the model must resist alone), and a reply to the attacker, stopped only by the checkpoint.

## 5. Cost

Per task: **3,104 input + 414 output tokens**, 3.0 steps. Cost per task / 300 tasks a month / 30,000 (100x): `gpt-oss-120b` or `gpt-4o-mini` $0.0007 / $0.21 / $21; `gpt-4.1-mini` $0.0019 / $0.57 / $57. The full eval cost about $0.03. Latency p50 13.2 s, p95 26.6 s including rate-limit waits. **What breaks first is the rate limit, not the bill** (free tier: 8,000 tokens/min, 200,000/day); real inboxes would also raise input tokens. List prices, to re-check.

## 6. What went wrong

Course key out of credits; injection tests the model never read, then one attack that still works; a stop rule that blocked recovery; one wrong scenario of our own; injection tests the model never saw; daily token limit found late. Details in `postmortem.md`.
