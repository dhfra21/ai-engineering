# Project 2: The Librarian

CS496 AI Engineering, Fall 2026. Brief: [`../project2-librarian.pdf`](../project2-librarian.pdf).

A question answering service over **Tunisian laws** (Journal Officiel, 2013 to 2026) in **Arabic and French**.
It retrieves with BM25 + vector search + a reranker, answers with `gpt-4o-mini`, cites the law and article
for every claim, and says "I don't know" when the corpus has no answer.

*Corpus pending instructor OK.* Deployed URL: *to add after deployment* (see `deploy/DEPLOY.md`).

## Setup (one command)

```bash
uv venv --python 3.12 .venv && uv pip install -p .venv/bin/python --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match torch -r requirements.txt && cp .env.example .env
```

Then put the course OpenAI key in `.env` (`OPENAI_API_KEY=...`, never commit it). Build the search index (3 minutes, $0.14):

```bash
.venv/bin/python -m src.index article-oai
```

## Run (one command)

```bash
.venv/bin/python -m uvicorn src.service:app --port 8000      # then open http://localhost:8000
```

`POST /ask {"question": "..."}` returns the answer, numbered citations, latency and cost; `POST /feedback` records
a thumbs up/down; `GET /health`. A link like `http://localhost:8000/?q=<question>` asks it directly.
Tests: `.venv/bin/python -m pytest -q`.

## Results

Retrieval, article chunking + OpenAI embeddings (`results/ablation.md` has every table, including fixed-size
chunks and the local e5 embeddings). *Recall@5 / MRR@10.*

| search | main set (100 questions) | paraphrased set (50 questions) |
|---|---|---|
| keyword only (BM25) | 93% / 0.90 | 32% / 0.21 |
| vector only | 92% / 0.82 | 66% / 0.48 |
| hybrid (RRF) | 94% / 0.89 | 58% / 0.39 |
| hybrid + reranker | **100% / 0.98** | **76% / 0.61** |

Latency: search 0.1 to 0.5 s, but the reranker adds 7 to 9 s per query on CPU. Generation costs about $0.0002 per
request. Generation results (correctness, faithfulness, citations, "I don't know"), the Week 8 optimisation and
are **to be added** (`report/report.md`, `optimisation.md`). We did not collect feedback from real users.

## Rebuild the corpus and the evaluation

```bash
.venv/bin/python -m src.ingest.iort_scrape list --years 2013-2026 --types law
.venv/bin/python -m src.ingest.iort_scrape fetch --years 2013-2026 --types law      # Arabic PDFs -> text
.venv/bin/python -m src.ingest.iort_scrape fetch-fr --years 2013-2026 --types law   # French text
python data/eval/build_eval.py                                    # data/eval/qa.jsonl + qa_hard.jsonl
.venv/bin/python -m eval.retrieval_eval --strategy article-oai    # recall@k, MRR for four search modes
.venv/bin/python -m eval.ablation                                 # tables -> results/ablation.md
.venv/bin/python -m eval.generation_eval --tag baseline           # answers, judged (needs the key)
```

The scraper is polite (1 request per second) and idempotent; the site's links are sometimes wired to the wrong
file, so each document is named by what its text says it is (`data/corpus/mismatch.log`). Details and known
problems of the corpus: [`data/corpus/README.md`](data/corpus/README.md).

## Share the index (optional)

Embedding is the only slow or paid step. `scripts/pack_index.sh article-oai` packs `embeddings.npy` + `meta.json`
for a GitHub release; `scripts/fetch_index.sh <asset-url> article-oai` unpacks it and `src.index` reuses it after
checking a hash of the chunks. Or simply rebuild with your own key.

## Layout

`src/` pipeline (`ingest/` scraper, `chunking.py`, `index.py`, `embed.py`, `retrieve.py`, `generate.py`, `service.py`) ·
`eval/` retrieval, generation and ablation scripts · `data/corpus/` source texts · `data/eval/` questions with answers
and source passages · `results/` outputs · `report/` report · `tests/` · `deploy/` + `Dockerfile` · `TASKS.md` work split ·
`design.md`, `optimisation.md`, `postmortem.md` still to write.

## Contributions

*Roles follow the team board; confirm and adjust names before freezing the repo.*

- **OK (OKmimech)**: corpus scraping and the French/Arabic data, chunking and the index, retrieval and the ablation
  (article vs fixed chunks, embeddings, paraphrased questions), the 174 evaluation questions, the FastAPI service and
  web page, deployment files, unit tests, the report draft.
- **DF (dhfra21)**: OpenAI switch and `answer()` testing, generation evaluation and abstention tuning, cost model and
  Week 8 optimisation, `design.md`, `optimisation.md`, `postmortem.md`, final clean-clone check.

## No API keys in this repo

`.env` is git-ignored; keys are read from the environment in `src/config.py` and are never hardcoded. Logs of user
questions and feedback (`logs/`) are git-ignored too.
