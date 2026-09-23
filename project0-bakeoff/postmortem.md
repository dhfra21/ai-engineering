# Postmortem

Eval run 2026-09-23. Written after the run, against what the data
actually shows — see `results/per_item.csv` for everything cited here.

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

- **Output format compliance was perfect; we over-engineered for it.**
  We expected to need fence-stripping or trailing-prose cleanup. Across
  all 150 responses, **zero** contained a markdown code fence and
  **every** non-empty response ended in a semicolon. The "output ONLY
  the SQL" instruction in `src/prompt.py` held on all three models,
  including the 7B. None of the defensive parsing we budgeted time for
  was needed.

- **Our latency numbers silently include API retry time.**
  `gpt-oss-120b` item 13 took **63.9 seconds** to produce **73 output
  tokens** — other items with similar token counts returned in about a
  second. That is not generation time. `run.py` constructs
  `Groq(max_retries=5)`, and `call_groq` starts its timer *before*
  `client.chat.completions.create(...)`, so when the SDK absorbs a 429
  and sleeps for the server's `Retry-After`, **the backoff is counted as
  model latency**. `gpt-oss-20b` item 34 (17.8 s for 298 tokens) looks
  like the same thing. Ironically, `call_gemini` gets this right — it
  times each attempt separately, with a comment explaining exactly why —
  and we did not carry that fix across when we swapped providers. Impact
  is limited: both outliers sit above p95, so the reported p50/p95 are
  unaffected, and Groq cost is computed from token usage rather than
  time. But the mean latency for the 120B is inflated by roughly a
  second, and had a third call stalled, p95 would have been wrong.

- **The 512-token cap cost the cheap model an item, and we scored it as
  a SQL failure.** `gpt-oss-20b` item 45 returned an **empty string**
  with `output_tokens = 512`, exactly the cap. GPT-OSS models bill
  reasoning tokens against the same budget, and the 20B reasons more
  verbosely than the 120B (205 vs 144 average output tokens), so it hit
  the ceiling before emitting any answer. `score.py` recorded this as
  "not a single read-only SELECT" — technically true, but it reads as a
  capability failure in the results table when it is a harness limit we
  set ourselves.

- **The open-weights model ran roughly 10x slower than we expected, for
  a reason we should have predicted.** `qwen2.5-coder:7b-instruct` at Q4
  is ~4.7 GB against the RTX 2050's 4 GB of VRAM, so Ollama offloads
  part of the model to CPU: **3.6 tokens/second**, a 14.1 s p50. We
  picked the model by parameter count without checking it against the
  card. The first call (19.7 s vs a 14.1 s median) also carries model
  load time, since we never issued a warm-up request.

- **Three of our five total misses are the same label ambiguity, not a
  model error.** `gpt-oss-20b` item 26 and `qwen7b` items 31 and 46 each
  added an unrequested `WHERE status = 'completed'` filter. The SQL is
  well-formed; it answers a slightly narrower question than the one
  asked. Our questions do not say whether cancelled and pending orders
  count, and our gold SQL silently assumes they do. A stricter reading
  of `data/LABELLING.md`'s "unambiguous" claim would have caught this
  before the run.

## Known deviations from the brief

- **Both API-tier models are the same base model family, two sizes.**
  `openai/gpt-oss-120b` and `openai/gpt-oss-20b` are OpenAI's own
  open-weight models, both served by Groq at two different sizes/costs,
  rather than two different labs' proprietary models. This still
  satisfies the brief's "top API model" / "cheap API model" split — same
  relationship (you call an API, you don't run the weights), same
  provider, two tiers Groq itself sells — but it does mean this bake-off
  measures "does model size matter" more than "does provider/architecture
  matter." Flagged in the report's section 3.

- **Cost figures reflect list price, not what we actually paid.** Actual
  spend collecting all 50 x 2 API results was $0 (Groq's free tier). This
  is intentional, not an oversight — see `src/config.py`'s top comment.

- **Temperature 0 did not give us determinism.** Re-running the two Groq
  models a day apart changed the generated SQL on 14/50 (120B) and 8/50
  (20B) items, with no change in accuracy. Expected for batched
  mixture-of-experts serving, but it means our headline 50/50 vs 48/50
  gap is within run-to-run noise. We report a single run per the brief;
  we should not claim the 120B is reliably better than the 20B on this
  evidence, only that it is at least as good.

- **The self-hosted hourly rate excludes hardware amortisation and our
  own time.** It prices electricity on a laptop we already own. Stated
  plainly in `results/HARDWARE.md` and the report's section 6, because
  including amortisation moves the break-even volume a lot.

## What we'd do differently

1. **Time each API attempt, not the whole retried call.** Move the timer
   inside the retry boundary in `call_groq` (or set `max_retries=0` and
   handle retries ourselves), the way `call_gemini` already does. Report
   retry count as its own column so a stalled call is visible instead of
   masquerading as a slow model.
2. **Issue a warm-up call to Ollama before the timed run**, and check the
   model's quantised size against available VRAM *before* picking it. The
   first-call penalty and the 10x CPU-offload slowdown were both
   predictable.
3. **Separate "wrong SQL" from "harness truncated the answer"** in
   `score.py`. An empty response at exactly `max_tokens` deserves its own
   bucket; folding it into execution failures overstates the cheap
   model's error rate.
4. **Resolve the order-status ambiguity in the question set** — either
   say "including cancelled orders" in the question text, or accept both
   readings in scoring. Three of five misses hang on this one unstated
   assumption.
5. **Run each model more than once.** With 50 items and non-deterministic
   serving, a 2-item gap is not a result. Three runs and a spread would
   cost nothing on the free tier and would let us say something honest
   about separation.

## What we learned

The headline is that **all three models are good at this task** — 100%,
96%, 94% — and the interesting differences are not accuracy. Every model
solved every easy item, and only 5 misses exist across 150 calls. On a
schema this small, model choice barely moves correctness.

What does move is everything around the model. The 7B is ~14x slower
because of a VRAM decision we made carelessly, not because it is a worse
SQL writer. The cheap model's one hard "failure" is a token budget we
chose. The most common error across all three is a question we wrote
ambiguously. Three of the five misses and one of the three models'
latency profiles trace back to our harness, not to the models.

We would ship `gpt-oss-120b` on Groq — fastest p50, no observed errors,
and $0.136/1k is not worth optimising. We would switch to the
self-hosted 7B only if data could not leave our infrastructure, where 94%
at zero marginal cost is a genuinely good trade. The full version of that
argument, with the break-even volumes, is in `report/report.md`.
