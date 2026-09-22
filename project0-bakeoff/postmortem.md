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

- **Temperature 0 is not achievable on Claude Opus 5.** The brief asks
  for identical sampling settings across all three models. Opus 5
  rejects `temperature` entirely (its 4.6+-generation sampling
  parameters were replaced by adaptive thinking + an `effort` control).
  We left `temperature` unset for Opus 5 and pinned it to 0 for Haiku 4.5
  and the Ollama model, which is the closest same-conditions setup the
  current API allows. See `src/models.py` for where this is handled.
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
