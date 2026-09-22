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

- _(e.g. did all three models produce parseable SQL on the first try, or
  did one of them wrap output in markdown fences despite the instruction
  not to?)_
- _(e.g. did the open-weights model need a retry loop, run out of VRAM,
  or produce noticeably slower/faster output than expected?)_
- _(e.g. did any item's gold label turn out to be ambiguous once real
  model output was compared against it?)_

## Known deviations from the brief

- **Both API-tier models come from the same provider (Google).** The
  brief's examples pair a top model and a cheap model either within one
  provider (Claude Opus 5 / Claude Haiku 4.5) or across providers — using
  Gemini for both tiers is explicitly one of the brief's own suggested
  pairings ("the top GPT or Gemini model" / "'mini' or 'Flash' models").
  We chose it specifically because Google AI Studio's free tier covers
  both `gemini-3.8-flash` and `gemini-3.5-flash-lite` at $0 actual cost,
  while `results/cost_summary.csv` still reports the published paid list
  price per the brief's "token counts x list price" instruction.
- **Cost figures reflect list price, not what we actually paid.** Actual
  spend collecting all 50 x 2 API results was $0 (free tier). This is
  intentional, not an oversight — see `src/config.py`'s top comment.
- _(add any other deviation you hit — different tokenizer counts for the
  self-hosted model, Ollama batching behavior, Gemini free-tier rate
  limits forcing a delay between calls, etc.)_

## What we'd do differently

_(one or two concrete things — e.g. "run the self-hosted model's calls
in a separate warm-up pass before timing latency, because the first call
included model load time and skewed p95")_

## What we learned

_(the actual point of Project 0 — which model would you pick, and what
would make you change that pick? Put the full answer in report.pdf; put
the short, honest version here.)_
