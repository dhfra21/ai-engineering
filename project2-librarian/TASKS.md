# Project 2: work split

Owners and due dates follow the team board. Status is as of 3 Nov 2026, evening.
**Each person needs the OpenAI key from the professor in their own `project2-librarian/.env`
(copy `.env.example`; never commit it).** Most tasks in the right-hand column below need it.

## DF

Remaining DF work was split with OK on 3 Nov, since OK's own tasks are done and deployment is
left for the last step. DF keeps everything that measures latency, because before/after numbers
only compare when they come from the same machine (DF's). OK takes the write-ups and checks that
need no measurement.

| Task | Owner | Due | Status |
|---|---|---|---|
| Switch `config.py` / `generate.py` to OpenAI, key in `.env` | DF | 6 Nov | **Done and checked with real calls** (generator `gpt-4o-mini`, judge `gpt-4.1-mini`; this project's key does not list `gpt-4o`) |
| Get corpus approval from the instructor | DF | 6 Nov | Message drafted; DF sends it |
| Test `answer()` end to end, Arabic and French | DF | 13 Nov | **Done** on `article-oai`: both languages correct, citing the gold article; unanswerable questions abstain. Found one prompt failure: a French question abstained in Arabic. Fixed: low-score abstention now answers in the question's language (`idk_for` in `src/generate.py`) |
| Choose and justify the vector DB / index | DF | 13 Nov | **Done**: flat files + brute-force cosine, justified in `design.md` |
| Write `eval/generation_eval.py` | DF | 20 Nov | **Done**, first real run in progress (see "Currently running"). Rows now also store the top retrieval score, and the models are warmed up before timing |
| Baseline numbers: p50/p95 latency, cost, accuracy | DF | 27 Nov | Running now on `article-oai`, 124 questions, `hybrid+rerank`, k = 5 → `results/generation_baseline.json` |
| Tune abstention threshold, fix prompt failures | DF | 20 Nov | Next, from the baseline rows (threshold tuned offline on `top_score`, no re-run) |
| Optimise: 50% cost or latency cut, at most 2 points lost | DF | 27 Nov | Next. Switches now reach the whole pipeline: `--n-candidates`, `--rerank-max-length`, `--skip-rerank-gap` in both eval scripts, and `N_CANDIDATES` / `SKIP_RERANK_GAP` / `INDEX` env vars in the service. Plan: choose the variant on retrieval only (cheap), confirm with one generation run |
| Record before/after numbers in `optimisation.md` | DF | 27 Nov | After the optimisation runs |
| Write `design.md` | DF | 4 Dec | **Done**: chunking (with the ablation), index choice, retrieval, generation, 8 known failure cases. Generation results get added after the baseline |
| Cost model: tokens and $ per request, today and at 100x | **OK** | 27 Nov | Moved from DF. Inputs: per-request tokens and $ in `results/generation_baseline.json` (`gen_cost`, `cost_per_request_usd`), index build cost in `data/index/*/meta.json`, prices in `src/config.py`. Include the query-embedding call for `-oai` indexes and the hosting cost |
| Write `postmortem.md` | **OK** | 4 Dec | Moved from DF. Material: the Windows `open()` encoding issue (needs `PYTHONUTF8=1`), the duplicated hour-long index builds before indexes were shared, the e5 vs OpenAI-embedding switch mid-project, the mislabelled source files, and whatever the baseline failures show |
| Final check: clean clone, no keys, no personal data | **OK** | 4 Dec | Moved from DF. Do it after the last push |

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

## Currently running (on DF's machine, 3 Nov 2026)

The generation baseline: `python -m eval.generation_eval --tag baseline --strategy article-oai`
(124 questions, about 6 s each, done around 21:50). Intermediate count: 84 of 96 correct. Do not
run heavy jobs on DF's machine until the optimisation runs are done, since they set the latency
numbers.

On Windows, run Python with `PYTHONUTF8=1`: several `open()` calls rely on the default encoding,
which is cp1252 there and fails on Arabic text.

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
