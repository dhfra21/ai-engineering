# Week 8: optimisation

**Target (from the brief):** cut p95 latency or cost per request by 50%, losing at most 2 points of accuracy,
measured before and after on the same test set.

**How it was measured.** The test set is the main eval set: 124 questions (100 answerable, 24 not) in Arabic and
French, run with `python -m eval.generation_eval --strategy article-oai --tag <tag> [switch]`. Accuracy is answer
correctness from the LLM judge (`gpt-4.1-mini`, with the fixed faithfulness numbering). Latency is end to end:
search, rerank and generation. Every row was run in one session, one after another, on one machine (DF's, 12-core
CPU) with nothing else heavy running. Each change was first measured alone against row 0, then the kept ones together.

**About the absolute latencies.** On the evening of 3 Nov the same configuration ran at p50 4.9 s. In the session
these rows come from, search was steadily about 4x slower, from the first question of row 0 to the last of the
final run. The cause was likely CPU throttling (power or heat), since no other heavy process was running. Within the
session the slowdown was constant, so the **relative** changes below are comparable. The absolute seconds are not
comparable with other sessions or machines. The percentage cuts are the result.

**Noise.** Generation and judging vary a little between runs of the same configuration (temperature 0 is not fully
deterministic, and neither is the judge). Two runs of the tuned configuration both gave 96%, but row 2 below lost
3 points even though the same change lost nothing in the retrieval-only test. Treat differences of 1-2 points as
within noise.

## Where the time and money go (row 0)

| stage | p50 | p95 |
|---|---|---|
| search: BM25 + OpenAI query embedding + cross-encoder rerank of 30 candidates | 13.9 s | 16.0 s |
| generation (`gpt-4o-mini`) | 2.5 s | 3.4 s |

The reranker accounts for almost all of the search time, and generation costs $0.00023 per request. So latency is
the target, and the reranker is where to cut.

## Results

| # | change | switch | p50 | p95 | cost per request | correctness | faithfulness | unanswerable refused | kept? |
|---|---|---|---|---|---|---|---|---|---|
| 0 | before: tuned prompt, no refusal threshold, rerank 30 candidates x 384 tokens, 5 chunks | none | 16.2 s | 19.3 s | $0.000229 | 96% | 96% | 20/24 | |
| 1 | fewer rerank candidates | `--n-candidates 10` | 7.7 s | 9.2 s (-52%) | $0.000223 | 94% (-2) | 95% | 22/24 | **yes: deployed** |
| 2 | shorter rerank input | `--rerank-max-length 256` | 11.8 s | 13.4 s (-31%) | $0.000220 | 93% (-3) | 94% | 21/24 | no |
| 3 | skip the reranker when the first search is confident | `--skip-rerank-gap` | not run | | | | | | no |
| 4 | fewer chunks sent to the model | `--k 3` | 16.0 s | 17.9 s (-7%) | $0.000165 (-28%) | 92% (-4) | 96% | 22/24 | no |
| 5 | cheaper generation model | `--model gpt-5-nano` | not run in full | | | | | | no |
| 6 | cache repeated questions | `CACHE_ANSWERS=1` | no repeats in the test set | | | | | | built in, off by default |
| 1+2 | a milder combination: 15 candidates x 256 tokens | `--n-candidates 15 --rerank-max-length 256` | 9.6 s | 11.0 s (-43%) | $0.000200 | 95% (-1) | 96% | 22/24 | no: misses the 50% |
| **final** | **row 1: 10 candidates x 384 tokens** | `--n-candidates 10` (service default `N_CANDIDATES=10`) | **7.7 s (-52%)** | **9.2 s (-52%)** | $0.000223 (-3%) | **94% (-2)** | 95% | 22/24 | **deployed** |

Result files: `results/generation_w8_<n>_*.json` (one per row) and `results/generation_w8_final_c15_l256.json`
(the 1+2 combination). Retrieval-only checks of the reranker settings, which chose which ones to run in full:
`results/retrieval_qa_article-oai_w8_*.json`.

**Result.** p95 latency fell from 19.3 s to 9.2 s (-52%) and p50 from 16.2 s to 7.7 s (-52%), with correctness 96% to
94% (-2 points), faithfulness 96% to 95%, and unanswerable questions refused 20/24 to 22/24. **The latency target is
met and the accuracy limit is met exactly, with no margin:** a 2-point drop is also within run-to-run noise (see
above), so the true loss could be 0 or 4 points. The milder combination (15 x 256) keeps accuracy (-1 point) but
cuts p95 by only 43%. Cost per request barely changed (-3%), so the cost target was not met (see "What was not done").

**Combining 1 and 2 at full strength (10 candidates x 256 tokens) was not run end to end.** Retrieval alone gave
recall@1 97%, recall@5 99% and search p95 -66% against 30 x 384, so it would probably cut more latency at the same
accuracy as row 1. It is the next run to make.

## Each change

**1. Fewer rerank candidates (30 to 10).** The cross-encoder scores every candidate, so its time is close to
proportional to their number. Search fell from 13.9 s to 5.5 s, and p95 from 19.3 s to 9.2 s (-52%), which meets the
target alone. It lost 2 points of correctness, exactly the limit, and is the deployed setting. Retrieval alone shows why: recall@1 fell from 97% to
96% and recall@5 from 100% to 99%. One French question (`q045-fr`), ranked first by the reranker with 30 candidates,
had its gold article outside the fused top 10, so with 10 candidates the reranker never saw it.

**2. Shorter rerank input (384 to 256 tokens).**
The reranker reads the first 256 tokens of each question-chunk pair instead of 384, so less compute per candidate. p95 fell 31%. Retrieval alone lost nothing (recall@1 97% to 98%,
recall@5 100%). The 3-point drop in correctness is larger than retrieval explains, so we read it as noise. The 1+2
combination (15 x 256) supports that reading: it lost only 1 point.

**3. Skip the reranker when the first search is confident.** Not measured in full, for lack of time on the measuring
machine. It interacts badly with the rest of the design: when the reranker is skipped, the returned scores are RRF
fusion scores, so any score-based refusal would mean something different on those requests. The fixed cut of
candidates and tokens already meets the target without that complication.

**4. Fewer chunks to the model (5 to 3).** This is the only cost lever that worked: prompt tokens fell, and cost per
request with it, by 28%. But correctness fell 4 points. Asking for complete answers needs the neighbouring articles
(penalties, exceptions) that chunks 4 and 5 often hold. Latency barely moved (-7%), because generation time follows
the answer's length, not the prompt's. Not kept.

**5. Cheaper generation model.** `gpt-5-nano` is a reasoning model. With our 500-token answer budget it spent all of
it on reasoning and returned an **empty answer**, at $0.00021, about what `gpt-4o-mini` costs for a full answer.
A larger budget would cost more than the current model. `gpt-4.1-nano` is not available on the course key (404).
Not kept, and not run in full.

**6. Cache repeated questions.** `CACHE_ANSWERS=1` in the service returns a stored answer for the same question, at
$0 and a few milliseconds. The test set has no repeated questions, so it cannot be measured on it. Its value depends
on real traffic: a class demo repeats the example questions, real users rarely do. It is off by default so that
logged latencies stay honest.

## What was not done

- **The refusal threshold was dropped**, not optimised. A threshold of 2.0 on the reranker score looked free on
  the main set but would refuse 74% of the paraphrased answerable questions (`results/threshold_check.md`). All
  rows above run without it, so "unanswerable refused" is the model's own refusal.
- **The cost target was not reached.** Generation costs about $0.0002 per request, and the only lever that cut it
  (row 4) cost 4 points. At this price, latency and hosting matter more: the reranker's CPU time decides how many
  workers the service needs (`results/cost_model.md`).

## Second session (4 Nov, morning): accuracy confirmed, latency method revised

The machine was back to normal speed, so rows 0 and 1 and the untried 10 x 256 combination were re-run
(`results/generation_w8b_*.json`). **Accuracy confirms the result**, with an even smaller loss:

| setting | correctness | faithfulness | unanswerable refused | cost per request |
|---|---|---|---|---|
| 30 x 384 (before) | 95% | 97% | 22/24 | $0.000227 |
| **10 x 384 (deployed)** | **94% (-1)** | 94% | 22/24 | $0.000223 |
| 10 x 256 | 93% (-2) | 93% | 22/24 | $0.000219 |

**Latency could not be compared from these runs.** In the middle of a run, the laptop's speed switched between normal
and about 3.5x slower: row 1's search took 5.2 s per question for the first 60 questions, then 1.5 s, and the
10 x 256 run did the opposite. Configurations run one after another can each catch a different phase. In matching
normal-speed stretches, search took 3.5 s with 30 candidates, 1.5 s with 10, and 1.2 s with 10 x 256 (-57% and
-66%). That agrees with the first session (-61%) and with the retrieval-only test (-66% for 10 x 256).

The fair way to measure this is `eval/latency_bench.py` (added): it times every setting on each question back to
back, in rotating order, so a slow phase hits all of them alike, and adds each question's measured generation time.
**It has not been run in full yet**, for lack of time. Running it once on an idle machine
(`python -m eval.latency_bench`, about 15 minutes, no LLM calls) gives the definitive end-to-end p50/p95 for the
report. The paraphrased-set generation runs (hand-off item 5) were also stopped before finishing.
