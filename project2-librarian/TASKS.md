# Project 2: work split

Owners and due dates follow the team board. Status is as of 3 Nov 2026.
**Blocker for most of the right-hand column: the OpenAI key from the professor must be put in
`project2-librarian/.env` (copy `.env.example`; never commit it).**

Status legend: done / written, not yet run for real / not started.

## DF

| Task | Due | Status |
|---|---|---|
| Switch `config.py` / `generate.py` to OpenAI, key in `.env` | 6 Nov | Code switched; **key missing**, no real API call made yet |
| Get corpus approval from the instructor | 6 Nov | To review (not code) |
| Test `answer()` end to end, Arabic and French | 13 Nov | Not started (needs key) |
| Choose and justify the vector DB / index | 13 Nov | Implementation is flat files + brute-force cosine; the justification is not written (goes in `design.md`) |
| Write `eval/generation_eval.py` | 20 Nov | Written and tested on fake data only; first real run also tests the judge |
| Tune abstention threshold, fix prompt failures | 20 Nov | Not started (needs real runs) |
| Cost model: tokens and $ per request, today and at 100x | 27 Nov | Not started. Per-request cost is already logged by the service |
| Baseline numbers: p50/p95 latency, cost, accuracy | 27 Nov | Retrieval baseline done (see below); generation baseline needs the key |
| Optimise: 50% cost or latency cut, at most 2 points lost | 27 Nov | Switches prepared in `src/retrieve.py` (skip reranker when confident, shorter rerank input, fewer candidates), all off by default. Main target: reranker at 7.4 s per query |
| Record before/after numbers in `optimisation.md` | 27 Nov | Not started |
| Write `design.md`, `optimisation.md`, `postmortem.md` | 4 Dec | Not started. Known failure cases are already listed in `data/corpus/README.md` |
| Final check: clean clone, no keys, no personal data | 4 Dec | Not started |

## OK

| Task | Due | Status |
|---|---|---|
| Fixed-window index + chunking ablation (article vs fixed) | 13 Nov | Fixed index built; evaluation of it was still running when this was written |
| Write `eval/ablation.py` for the final retrieval table | 13 Nov | Written; prints and saves `results/ablation.md` |
| Add harder eval cases and re-run the ablation | 13 Nov | 50 paraphrased questions written (`data/eval/qa_hard.jsonl`); re-run in progress |
| Decide final chunking + search method from the ablation | 13 Nov | Waiting on the results above |
| FastAPI service: `/ask` and `/feedback` | 20 Nov | Written (`src/service.py`) and tested with a stubbed pipeline; never run with real models |
| Web page: right-to-left Arabic, citations, thumbs up/down | 20 Nov | Written inline in the service; not yet looked at in a browser |
| Deploy to a public URL and collect classmate feedback | 20 Nov | Not started (pick hosting first: CPU only, about 1-2 GB RAM for the models) |
| pytest tests: chunking, gold matching, scraper parsers | 27 Nov | Done: 34 tests, also covering text normalisation, retrieval, service and generation eval |
| Report (max 6 pages) + README with Contributions | 4 Dec | README updated for the corpus; report not started |

## Currently running (on Claude's machine, 3 Nov 2026)

One background job is running the retrieval evaluation, one run after another:

1. main question set on the **fixed-window** index (started first, still going)
2. paraphrased set on the **article** index
3. paraphrased set on the **fixed-window** index

Each run takes about 15 minutes, because the reranker needs about 7 seconds per query on
CPU, so all three finish roughly 45 minutes after they started. They write
`results/retrieval_<set>_<strategy>.json`. When they are all there, run
`python -m eval.ablation` to get the tables in `results/ablation.md`. That unblocks OK's
"decide final chunking + search method". Do not start another heavy job on the same
machine meanwhile; it would skew the latency numbers.

Nothing else is running. Everything after this point needs the OpenAI key.

## What already exists

- Corpus (Arabic and French laws, 2013-2026), scraper and `data/corpus/README.md`.
- Article-aware chunking, BM25 + dense + RRF + reranker retrieval, article index.
- 124 evaluation questions in Arabic and French (`data/eval/qa.jsonl`), plus the paraphrased set.
- Retrieval results, main set, article chunking (100 answerable questions):

| search | recall@5 | MRR@10 | search p50 |
|---|---|---|---|
| keyword only (BM25) | 93% | 0.898 | 66 ms |
| vector only | 91% | 0.812 | 152 ms |
| hybrid | 93% | 0.874 | 159 ms |
| hybrid + reranker | 100% | 0.985 | 7.4 s |

## Hand-off notes

- **Not on GitHub yet:** the code written since the first push (`src/service.py`, `eval/generation_eval.py`,
  `eval/judge.py`, `eval/ablation.py`, the OpenAI switch in `src/config.py` / `src/generate.py`, the
  retriever options, `tests/`, `data/eval/qa_hard.jsonl`). It is on Claude's machine and gets pushed
  in a later commit; ask for it before starting on those tasks.
- Building an index takes 45-60 minutes on CPU. Do not rebuild it: ask for the built files
  (`data/index/` is git-ignored because of its size) or build once and share.
- The scraper is polite (1 request per second) and idempotent. See `data/corpus/README.md`.
- The brief's deadlines: working version end of Week 7; optimised version and demo in the
  first session of Week 9.
- Unit tests: `.venv/bin/python -m pytest -q`.
