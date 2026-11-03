# Project 2: work split

Owners and due dates follow the team board. Status is as of 3 Nov 2026.
**Each person needs the OpenAI key from the professor in their own `project2-librarian/.env`
(copy `.env.example`; never commit it).** Most tasks in the right-hand column below need it.

## DF

| Task | Due | Status |
|---|---|---|
| Switch `config.py` / `generate.py` to OpenAI, key in `.env` | 6 Nov | **Done and checked with real calls** (generator `gpt-4o-mini`, judge `gpt-4.1-mini`; this project's key does not list `gpt-4o`) |
| Get corpus approval from the instructor | 6 Nov | To review (not code) |
| Test `answer()` end to end, Arabic and French | 13 Nov | Not started. Do it on an idle machine so latency numbers are clean |
| Choose and justify the vector DB / index | 13 Nov | Implementation is flat files + brute-force cosine; the justification still has to go in `design.md` |
| Write `eval/generation_eval.py` | 20 Nov | Written and unit-tested on fake data; **first real run still to do** (it also exercises the judge) |
| Tune abstention threshold, fix prompt failures | 20 Nov | Not started (needs real runs) |
| Cost model: tokens and $ per request, today and at 100x | 27 Nov | Not started. Per-request cost is already logged by the service; index build cost is in `meta.json` |
| Baseline numbers: p50/p95 latency, cost, accuracy | 27 Nov | Retrieval baseline done (see below); generation baseline needs a real eval run |
| Optimise: 50% cost or latency cut, at most 2 points lost | 27 Nov | Switches prepared in `src/retrieve.py` (skip reranker when confident, shorter rerank input, fewer candidates), all off by default. Main target: reranker at 7-9 s per query. Also candidate: OpenAI embeddings with fewer dimensions (`--dims`) |
| Record before/after numbers in `optimisation.md` | 27 Nov | Not started |
| Write `design.md`, `optimisation.md`, `postmortem.md` | 4 Dec | Not started. Known failure cases are already listed in `data/corpus/README.md` |
| Final check: clean clone, no keys, no personal data | 4 Dec | Not started |

## OK

| Task | Due | Status |
|---|---|---|
| Fixed-window index + chunking ablation (article vs fixed) | 13 Nov | **Done.** Article chunking is better at the top ranks (tables in `results/ablation.md`) |
| Write `eval/ablation.py` for the final retrieval table | 13 Nov | **Done** (`python -m eval.ablation`) |
| Add harder eval cases and re-run the ablation | 13 Nov | **Done.** 50 paraphrased questions in `data/eval/qa_hard.jsonl`; far harder (see below) |
| Decide final chunking + search method from the ablation | 13 Nov | **Ready to decide.** Results so far favour article chunking, with the reranker; note hybrid is worse than vector-only on paraphrased questions |
| FastAPI service: `/ask` and `/feedback` | 20 Nov | Written (`src/service.py`) and tested with a stubbed pipeline; never run with real models |
| Web page: right-to-left Arabic, citations, thumbs up/down | 20 Nov | Written inline in the service; not yet looked at in a browser |
| Deploy to a public URL and collect classmate feedback | 20 Nov | Not started (pick hosting first: CPU only, about 1-2 GB RAM for the models) |
| pytest tests: chunking, gold matching, scraper parsers | 27 Nov | **Done:** 37 tests (`.venv/bin/python -m pytest -q`) |
| Report (max 6 pages) + README with Contributions | 4 Dec | README updated; report not started |

## Currently running (on Claude's machine, 3 Nov 2026)

The retrieval evaluation of the new **OpenAI-embeddings index** (`article-oai`): main question set,
then paraphrased set, about 15 minutes each (the reranker takes 7-9 s per query on CPU). When it is
done, `python -m eval.ablation` will include it. Nothing else is running.

## The indexes

| Index | Embeddings | Build time | Cost |
|---|---|---|---|
| `article` | local e5-small, 384 dims | 57 min on CPU | 0 |
| `fixed` | local e5-small, 384 dims | 44 min on CPU | 0 |
| `article-oai` | OpenAI `text-embedding-3-small`, 1536 dims | **166 s** | **$0.135** |

Indexes are not in git (size). To avoid rebuilding: the owner packs the embeddings with
`scripts/pack_index.sh article-oai`, uploads `dist/librarian-index.tar.gz` to a GitHub release
(tag `index-v1`), and the teammate runs `scripts/fetch_index.sh <asset-url> article-oai`.
See the README section "Share the index". *The release has not been created yet.*

## What already exists

- Corpus (Arabic and French laws, 2013-2026), scraper and `data/corpus/README.md`.
- Article-aware chunking, BM25 + dense + RRF + reranker retrieval.
- 124 evaluation questions in Arabic and French (`data/eval/qa.jsonl`), plus 50 paraphrased ones.
- Retrieval results (recall@5 / MRR@10), article chunking, e5 embeddings:

| search | main set | paraphrased set |
|---|---|---|
| keyword only (BM25) | 93% / 0.90 | 32% / 0.21 |
| vector only | 91% / 0.81 | 64% / 0.51 |
| hybrid | 93% / 0.87 | 58% / 0.39 |
| hybrid + reranker | 100% / 0.985 | 74% / 0.60 |

The main set reuses the laws' own wording, which flatters keyword search; the paraphrased set is
the honest test.

## Hand-off notes

- The brief's deadlines: working version end of Week 7; optimised version and demo in the
  first session of Week 9.
- The scraper is polite (1 request per second) and idempotent. See `data/corpus/README.md`.
- Do not run heavy jobs while a latency measurement is running; they skew each other.
