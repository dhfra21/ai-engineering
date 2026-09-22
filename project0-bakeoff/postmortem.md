# Postmortem

_Fill this in after running the eval for real. A postmortem with no
problems loses points — write down what actually went wrong, not what
should have gone wrong._

## What we set out to do

Compare a top-tier API model, a cheap API model, and a self-hosted
open-weights model on one-shot text-to-SQL generation against a small
seeded retail database, using execution accuracy on 50 hand-checked
questions.

## What actually happened

- **We tried Google Gemini's free tier first and abandoned it.**
  `gemini-3.8-flash`'s free tier turned out to cap at 5 requests/minute.
  Firing all 50 calls back-to-back with no pacing blew through that
  after the 5th call — 96% of the first real run came back as
  `429 RESOURCE_EXHAUSTED`. We wrote a retry loop that honored the
  server's suggested wait, but at 5 RPM a full 50-item run would still
  take 10+ minutes of mostly waiting. We switched to Groq
  (`openai/gpt-oss-120b` / `openai/gpt-oss-20b`) instead, whose free
  tier allows 30 requests/minute — the run finished without needing the
  aggressive retry logic Gemini required (Groq's SDK retries 429/5xx on
  its own, honoring `Retry-After`).
- _(e.g. did both Groq models produce parseable SQL on the first try, or
  did one wrap output in markdown fences despite the instruction not to?)_
- _(e.g. did the open-weights model need a retry loop, run out of VRAM,
  or produce noticeably slower/faster output than expected?)_
- _(e.g. did any item's gold label turn out to be ambiguous once real
  model output was compared against it?)_

## Known deviations from the brief

- **Both API-tier models are the same base model family, two sizes.**
  `openai/gpt-oss-120b` and `openai/gpt-oss-20b` are OpenAI's own
  open-weight models, both served by Groq at two different sizes/costs,
  rather than two different labs' proprietary models. This still
  satisfies the brief's "top API model" / "cheap API model" split — same
  relationship (you call an API, you don't run the weights), same
  provider, two tiers Groq itself sells — but it does mean this bake-off
  measures "does model size matter" more than "does provider/architecture
  matter." Worth flagging in the report's choice paragraph.
- **Cost figures reflect list price, not what we actually paid.** Actual
  spend collecting all 50 x 2 API results was $0 (Groq's free tier). This
  is intentional, not an oversight — see `src/config.py`'s top comment.
- _(add any other deviation you hit — different tokenizer counts for the
  self-hosted model, Ollama batching behavior, etc.)_

## What we'd do differently

_(one or two concrete things — e.g. "run the self-hosted model's calls
in a separate warm-up pass before timing latency, because the first call
included model load time and skewed p95")_

## What we learned

_(the actual point of Project 0 — which model would you pick, and what
would make you change that pick? Put the full answer in report.pdf; put
the short, honest version here.)_
