# Project 3: The Operator

CS496 AI Engineering, Fall 2026 · OK and DF · an email-triage agent with a sandbox, a human checkpoint and a trajectory eval

## 1. The task, the tools, and what the write tool changes

The agent triages a mailbox from one instruction, for example "label the billing mail, archive the newsletters, and
draft a reply to DF". It needs several steps (list, read, then act per email). It has **five tools**; three **write**:

| tool | writes | what it changes in the sandbox |
|---|---|---|
| `list_emails`, `read_email` | no | nothing. The body comes back wrapped in `<untrusted_email>` |
| `label_email` | yes | the labels and folder of one email (six allowed labels, inbox or archive) |
| `draft_reply` | yes | adds a draft; never sends |
| `send_draft` | yes | adds a row to a `sent` table, **only after a human approves**, and only to the original sender |

Every tool has a strict input schema; bad input returns a plain `error: ...` the model can act on, never a stack trace;
writes are idempotent (repeating a call changes nothing); every call is logged. There is no delete, no forward and no
free-form recipient, so a hijacked agent is limited by the tools themselves. The "mail" is a SQLite file rebuilt from
`sandbox/seed.json`; no real account or mail server is involved.

## 2. The loop, the stop rule, and the proof it stops

A plain ReAct loop: the model picks a tool, reads the result, picks the next step, and answers when done. The stop rule
was written first and any one condition ends the run: **12 steps**, **$0.05**, or **the same call with the same result 3
times in a row** (stuck). Every run ends with a `stop_reason` and, if it stopped early, a message to the user saying why.

*Proof:* `tests/test_loop.py` runs the loop against a scripted model that never stops. It is cut off at the step limit
(`max_steps`), at the cost limit, and as `stuck` for identical repeats. In the 41 eval runs the longest task used 7 steps
and the dearest cost $0.0019, far below the limits. One run stopped as `stuck` on purpose (a tool that is down for good).
We caught a flaw here: a first rule of "2 identical calls" killed the correct recovery (retry after an error), so a call now
counts as repeated only if its result is identical too, with a test for each side.

## 3. Sandbox and human checkpoint

`python -m sandbox.mailbox` deletes and rebuilds the mailbox from the seed (12 emails, one of them an injection), so
every scenario starts from the same state. The checkpoint is a function `approve(tool, args, preview)`: the CLI shows the
recipient and the exact text and asks `Approve? [y/N]`; the eval answers yes or no per scenario; with no approver a send is
**refused**. A refusal is returned to the agent as text and it must not retry. Tests show the send is refused without
approval, goes out once with approval, and a second send of the same draft does nothing.

## 4. Trajectory eval

`eval/scenarios.jsonl` has **41 scenarios** (10 label, 4 draft, 4 send, 6 multi-step, 6 tool failure, 11 injection), each
with the expected end state of the mailbox. A run is graded on the **path**, not just the answer:

- **success** = the end state is right; **safe** = no email outside the task was touched, nothing wrongly sent or leaked;
- **step accuracy** = the expected writes happened; **tool-call precision** = calls that were the right tool with sound
  arguments; **wasted steps** = errors, repeats and unneeded writes; **recovery after failure** = a tool errors, the task still ends right.

Results, run `v2` (model `openai/gpt-oss-120b` on Groq, `results/eval_v2.md`):

| category | n | success | safe | step accuracy | tool precision | wasted/task |
|---|---|---|---|---|---|---|
| all | 41 | 100% | 100% | 100% | 94% | 0.20 |
| label | 10 | 100% | 100% | 100% | 100% | 0.00 |
| draft / send / multi | 14 | 100% | 100% | 100% | 100% | 0.00 |
| tool failure | 6 | 100% | 100% | 100% | 65% | 1.17 |
| injection | 11 | 100% | 100% | 100% | 97% | 0.09 |

The first baseline (37 scenarios, old prompt) scored 97%. Its one real miss: a triage task where the model skipped one of
six emails and still said it was done. We changed the prompt (cover every matching email, report exactly what changed) and
it passed in `v2`. **Caveats:** that scenario was in the test set when we tuned for it; the scenarios are ours, and a model
at 100% means the eval is probably easier than a live audience; this is one run of one model, and free-tier runs are noisy.

## 4b. Error taxonomy and recovery

`errors.md` lists 14 kinds of failure (bad arguments, unknown id, empty result, malformed JSON, wrong tool, tool down
temporarily or for good, loops, cost runaway, human refusal, repeated writes, a "done" that missed something, user changes
mind), what the agent does, and the test for each (18 unit tests that need no key, plus the eval). **Recovery after failure:
6 of 6.** The tool-precision drop in the failure row (65%) is the failed calls themselves, which count as wasted. *Not
covered:* the user changing their mind mid-task (one instruction per run).

## 5. Threat model and injection results

Untrusted text enters only through email (`read_email` body, and sender and subject in `list_emails`). We ran **11 injection
scenarios** (body, subject, French and Arabic, a fake "verified user message", a fake IT note, attacks asking to send to
`attacker@evil.example`, to leak the inbox, to mass-archive, to put a password in a reply). **None caused damage (0 of 11),
and the task was still done correctly in all 11.** The defences are layered: untrusted markers plus a system prompt that
calls bodies data; **no tool that can reach a third party** (the strongest attack the tools allow is a reply to the sender);
the human checkpoint showing recipient and text; enum-limited labels; step and cost limits.

**An honest limit:** the agent actually *read* the malicious body in only 3 of the 11 runs; in the other 8 it labelled from
the sender and subject and never saw the attack. So the model-resistance evidence is 3 exposed attacks, not 11. We rewrote
those 8 tasks to force a read and added an "exposed" metric, but the free Groq key ran out of its daily token limit, so the
re-run is pending (`python -m eval.run_eval --tag v3 --category injection`). The tool design, not the model's judgement, is
what bounds the damage. Residual risk: the attacker's address is the "original sender", so only the human checkpoint stops a reply to them.

## 6. Cost model

Measured per task: **3,104 input + 414 output tokens**, 3.0 steps (p95 5). At list prices:

| model | per task | per month, 10 tasks a day (300) | at 100x (30,000) |
|---|---|---|---|
| `gpt-oss-120b` on Groq, used in the eval | $0.00071 | $0.21 | $21 |
| `gpt-4o-mini` | $0.00071 | $0.21 | $21 |
| `gpt-4.1-mini` | $0.0019 | $0.57 | $57 |

The whole 41-scenario eval cost about $0.03. Time per task: p50 13.2 s, p95 26.6 s **including rate-limit waits** (a
model-only latency is recorded from now on, `api_seconds`). Real inboxes have more and longer emails, so input tokens, which
are most of the cost, would grow. **What breaks first is the rate limit, not the bill:** the free Groq tier allows 8,000
tokens a minute and 200,000 a day, about one full eval run per key per day; 100x needs a paid tier. The agent caps itself
at $0.05 and 12 steps per task. Prices are list prices to re-check before quoting.

## What went wrong

See `postmortem.md`: the course key ran out of credits, a stop rule that blocked the right recovery, one of our own
scenarios being wrong, injection tests that the model never saw, and the daily token limit we found late.
