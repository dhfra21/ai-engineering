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
| Write `eval/generation_eval.py` | DF | 20 Nov | **Done** and run for real (baseline, tuned, Week 8 rows). Rows store the top retrieval score; models are warmed up before timing |
| Baseline numbers: p50/p95 latency, cost, accuracy | DF | 27 Nov | **Done**: `results/generation_baseline.json` (87% correct, p95 5.75 s, $0.00021) and, for Week 8, row 0 re-run in the measuring session (`results/generation_w8_0_tuned.json`) |
| Tune abstention threshold, fix prompt failures | DF | 20 Nov | **Done.** Prompt fix: 87% to 96% correct. Threshold 2.0 tested and **dropped** after OK's check (refuses 74% of paraphrased answerable questions); the service default is off |
| Optimise: 50% cost or latency cut, at most 2 points lost | DF | 27 Nov | **Done: latency target met.** Reranking 10 candidates instead of 30: p95 -52%, correctness 96% to 94% (-2, the limit). Now the service default (`N_CANDIDATES=10`). Cost target not met (-3%). Next run to try: 10 candidates x 256 tokens |
| Record before/after numbers in `optimisation.md` | DF | 27 Nov | **Done** (`optimisation.md`), and the same table in report section 5 |
| Write `design.md` | DF | 4 Dec | **Done**, including generation results and the Week 8 setting |
| Cost model: tokens and $ per request, today and at 100x | **OK** | 27 Nov | **Script + preliminary numbers done**: `python -m eval.cost_model` writes `results/cost_model.md` (about $0.00023 per request, 7.6 s p50; $0.68/month today, $68/month fees + about $120 hosting at 100x, assumptions listed). Preliminary because it uses 7 real service requests. **Re-run on the baseline when DF pushes `results/generation_baseline.json`:** `python -m eval.cost_model` |
| Write `postmortem.md` | **OK** | 4 Dec | **Done** (including section 9, generation failures). Add anything the Week 8 runs teach us |
| Final check: clean clone, no keys, no personal data | **OK** | 4 Dec | **Preliminary check done** on a fresh clone (see below). **Run it again after the last push** |

## OK

| Task | Due | Status |
|---|---|---|
| Fixed-window index + chunking ablation (article vs fixed) | 13 Nov | **Done.** Article chunking is better at the top ranks (tables in `results/ablation.md`) |
| Write `eval/ablation.py` for the final retrieval table | 13 Nov | **Done** (`python -m eval.ablation`) |
| Add harder eval cases and re-run the ablation | 13 Nov | **Done.** 50 paraphrased questions in `data/eval/qa_hard.jsonl`; far harder (see below) |
| Decide final chunking + search method from the ablation | 13 Nov | **Done:** article chunking, hybrid search + reranker, OpenAI embeddings (`article-oai`). Reasons in `report/report.md` section 3. Open question for DF: hybrid is worse than vector-only on paraphrased questions (a lower BM25 weight in the fusion may help) |
| FastAPI service: `/ask` and `/feedback` | 20 Nov | **Done and run for real** (Arabic and French questions, feedback, protected `/admin/export` to download logs). 38 tests |
| Web page: right-to-left Arabic, citations, thumbs up/down | 20 Nov | **Done.** Checked in headless Chrome: Arabic answers render right to left, numbered citations, thumbs; `/?q=...` asks directly |
| Deploy to a public URL (classmate feedback **dropped by decision**; the service still logs thumbs up/down) | 20 Nov | **Files ready, not deployed.** `Dockerfile` + `deploy/DEPLOY.md` (Hugging Face Spaces, free CPU). The container build is untested (no Docker on the dev machine). Needs an HF account and the secrets `OPENAI_API_KEY`, `ADMIN_TOKEN`: a manual step |
| pytest tests: chunking, gold matching, scraper parsers | 27 Nov | **Done:** 37 tests (`.venv/bin/python -m pytest -q`) |
| Report (max 6 pages) + README with Contributions | 4 Dec | README done (confirm the Contributions names). Report draft is 3 pages (`report/report.md`, PDF with `python report/build_pdf.py`); sections 4 and 5 and the cost numbers are marked **[TO FILL]** and depend on DF's runs |

## Currently running (4 Nov 2026)

Nothing. The Week 8 runs are done (`results/generation_w8_*.json`, `results/w8_runs.log`). They ran in one session
during which DF's machine was steadily about 4x slower than the evening before, likely CPU throttling. So their
**percentages** are comparable with each other and their absolute seconds are not comparable with other runs
(explained in `optimisation.md`).

Report: sections 4-5 filled; `python report/build_pdf.py` now also finds Chrome on Windows (5 pages). OK: the
deployed URL, then the final clean-clone check after this push.

## Report handoff: what DF must supply when the Week 8 runs are done

The report (`report/report.md`, 5 pages of 6) is finished except what needs DF's machine. Everything else is written
from real runs. Open `report/report.md` section 5: every cell marked **[DF]** is yours.

1. **Section 5 table** (one row per change, then the final combination). Columns: p50, p95, cost per request,
   correctness, faithfulness, unanswerable refused, kept or not. Take them from `results/generation_<tag>.json`
   (`summary`). Use `--tag` per variant, same 124 questions, same machine, nothing else running.
2. **Row 0 must come from the same session as the variants.** Today it mixes DF's tuned run (latency, correctness 96%) with
   OK's re-judged run (faithfulness 96%, different machine). Re-run the tuned configuration once after pulling the judge
   fix (`--min-score 2.0`) and use that for row 0.
3. **The "Result" sentence and "What did not work"** in section 5: the final latency and cost against the baseline,
   in percent, and whether the 50% target and the 2-point limit were met; and the changes that failed, with numbers.
4. **`optimisation.md`**: the same table with a sentence per change (the brief asks for it separately). Copy the numbers
   from the report so the two agree.
5. **The refusal threshold: do not use it.** `results/threshold_check.md` shows 2.0 would wrongly refuse 74% of the paraphrased
   answerable questions (40% even at 0). Re-run the tuned prompt **without** `--min-score` on `qa` and, if you can, on `qa_hard`
   (`--set qa_hard`), and use those numbers for section 4/5 (the report currently quotes the run with 2.0 and says so).
6. **If the skip-reranker option is kept**, the returned scores are fusion scores, so the threshold must not be
   applied to those answers (see the docstring in `src/retrieve.py`); say how you handled it.
7. **The worker price** in the cost model ($30 per month, an assumption) can be replaced by a real quote:
   `python -m eval.cost_model --worker-usd-month <price>`; then update the cost table in section 6.
8. Rebuild the PDF with `python report/build_pdf.py` and check it is still at most 6 pages.

OK: the deployed URL (README and report), then the final clean-clone check after the last push.

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

## Clean-clone check (OK, 3 Nov, commit `beaf9ca`)

Done on a fresh clone of GitHub, following the README only:

- **Secrets:** none in the tree or in the whole history (only placeholders such as `OPENAI_API_KEY=...`). `.env`,
  `.venv`, indexes, raw PDFs and logs are not tracked.
- **Personal data:** none (no emails; the phone-like matches in the corpus are budget amounts; the corpus is public
  legal text).
- **Setup command:** works (dependencies installed from `requirements.txt`).
- **Tests:** 42 passed.
- **Index:** `python -m src.index article-oai` built 15,831 chunks in 149 s for $0.135.
- **Run:** the service started, `/health` ok, and a French question was answered with the right citation
  (`Loi n° 2015-37, Art. 8`) in 7.1 s.

Not covered: the Docker build (no Docker on this machine) and the deployed URL. **Run this check again after the
last push**, when the baseline, `optimisation.md` and the final report are in.
