# Design: the Operator (email inbox triage)

**Task.** Given an instruction ("archive the newsletters, label billing mail, draft a reply to DF"), the agent works
through a sandboxed mailbox in several steps. Three tools change state: labels/folders, drafts, and a gated send.

**Why this task passes the brief's five checks:** it needs several steps (list, read, then act per email); `label_email`,
`draft_reply` and `send_draft` change something; the mailbox is a SQLite file rebuilt from `sandbox/seed.json`; the
natural human checkpoint is the send; and 30+ scenarios, including tool failures, are easy to write (we have 41).

## How a run works

```
task ──> loop (agent/loop.py) ──> model picks a tool ──> run_tool (agent/tools.py) ──> sandbox (SQLite)
              ^                                                 |
              └──────────── result text (or "error: ...") ──────┘
 stops when: model answers without a tool | 12 steps | $0.05 | same call+result 3 times
```

Plain ReAct with OpenAI-style tool calling. No multi-agent design: one agent with five tools is enough here.

## The tools (`agent/tools.py`)

| Tool | Writes? | Notes |
|---|---|---|
| `list_emails(folder)` | no | id, sender, subject, labels |
| `read_email(email_id)` | no | body wrapped in `<untrusted_email>...</untrusted_email>` |
| `label_email(email_id, label, folder?)` | **yes** | label must be one of 6; folder inbox or archive. Set semantics, so repeating it changes nothing |
| `draft_reply(email_id, body)` | **yes** | keyed by hash(email, body): the same draft twice is one draft. Never sends |
| `send_draft(draft_id)` | **yes** | needs the human `approve()` to say yes; only replies to the original sender; already-sent drafts are skipped |

There is deliberately **no delete, no forward and no free-form recipient**: the worst a hijacked agent can do is bounded by the tools.

## Decisions and why

- **Stop rule written first** (`config.py`): `MAX_STEPS`=12, `MAX_COST_USD`=0.05, `MAX_REPEAT_CALLS`=3. Proof: `tests/test_loop.py`
  uses a scripted model that never stops. A retry after an error must not count as stuck (see `postmortem.md` section 3).
- **Human checkpoint = a function** (`approve(name, args, preview)`): the CLI asks you; the eval auto-answers yes/no per scenario; with no approver, sends are refused.
- **Injected model client** (`llm=`) and **injected tool runner** (`runner=`): lets tests script the model and lets the eval make tools fail, with no API key.
- **Eval grades the end state, not just the answer**: it compares the mailbox after the run with the expected one. Touching any email the task did not name counts as unsafe.
- **Provider**: Groq `openai/gpt-oss-120b` (free) after the course OpenAI key ran out of credits. Switch with `LLM_PROVIDER` in `.env`.

## Known limits

One instruction per run (no mid-task change of mind); one model; seed mailbox is small (12 emails); scenarios were written by us, so
the model scoring near 100% means the eval is probably easier than a live audience.
