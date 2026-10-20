# Project 2 — The Librarian

CS496 AI Engineering, Fall 2026, Weeks 5–8. Brief: [`../project2-librarian.pdf`](../project2-librarian.pdf).

**Corpus:** Tunisian laws from the *Journal Officiel* (Imprimerie Officielle,
iort.gov.tn), 2013–2026: 171 Arabic texts and 179 French translations
(about 12 million characters; budget and finance laws are the largest).
Users: law students and citizens asking in Arabic or French. Questions are
checkable against the article they come from. *(Pending instructor OK.)*

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install -p .venv/bin/python --extra-index-url https://download.pytorch.org/whl/cpu \
  --index-strategy unsafe-best-match torch -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY
```

Machine is CPU-only, so embeddings (`multilingual-e5-small`) and the reranker
(`mmarco-mMiniLMv2`) are small multilingual models. `pdftotext` (poppler) must be installed.

## Build the corpus and the index

```bash
.venv/bin/python -m src.ingest.iort_scrape list --years 2013-2026 --types law
.venv/bin/python -m src.ingest.iort_scrape fetch --years 2013-2026 --types law      # Arabic PDFs -> text
.venv/bin/python -m src.ingest.iort_scrape fetch-fr --years 2013-2026 --types law   # French text
.venv/bin/python -m src.index article            # chunk + embed + BM25 tokens (~25 min on CPU)
```

The scraper is polite (1 request per second) and idempotent. The site's own
links are sometimes wired to the wrong file, so each document is named by what
its text says it is; mismatches are logged in `data/corpus/mismatch.log`.

## Evaluate

```bash
python data/eval/build_eval.py                    # data/eval/qa.jsonl: 124 questions (AR+FR)
.venv/bin/python -m eval.retrieval_eval           # recall@k, MRR, ablation across search modes
```

## Layout

`data/corpus/` source texts (`txt/` Arabic, `fr/` French, `raw/` PDFs git-ignored) ·
`data/eval/` questions with answers and source passages · `data/index/` built index (git-ignored) ·
`src/` pipeline + service · `eval/` retrieval/generation eval and ablation ·
`results/`, `report/` · `design.md`, `optimisation.md`, `postmortem.md` to come.
