# Design

The Librarian answers questions about Tunisian laws (Journal Officiel, 2013-2026) in
Arabic or French, from 171 Arabic and 179 French law texts, with a citation to the
article for every claim. Corpus details and how it was scraped:
[`data/corpus/README.md`](data/corpus/README.md).

```
offline   corpus txt -> chunk (by article) -> BM25 tokens + embeddings -> data/index/<name>/
online    question -> BM25 top 30 + vector top 30 -> RRF fusion -> cross-encoder rerank -> top 5
          -> LLM answers from those 5 only, citing [n] -> "I don't know" if not in the sources
```

## Chunking: one chunk per article

Laws are already divided into articles (الفصل / Article), and users ask about articles
("what does article 30 say", "within what delay..."). So the main strategy
(`src/chunking.py`, `article`) cuts each law at article headings:

- Articles longer than 1,200 characters are split at line or sentence boundaries,
  with 150 characters of overlap.
- Articles shorter than 200 characters are merged with the following ones, up to the
  size limit, so very short articles like "this law enters into force..." still carry
  context.
- Every chunk starts with a header such as `Loi n° 2016-41 — Art. 2`, so it can be
  understood and cited on its own, and so BM25 can match law and article numbers.
- Text before the first article (title, visas) is its own chunk. A law with no
  article markers falls back to the fixed window.

The article index has 15,831 chunks (Arabic and French together).

**Tested against a fixed window** (`fixed`: 1,200 characters, 150 overlap, ignoring
article boundaries; 12,183 chunks), with the same retrieval stack and both question
sets (`results/ablation.md`, local e5 embeddings):

| question set | chunking | recall@1 | recall@5 | MRR@10 (hybrid + rerank) |
|---|---|---|---|---|
| main (100 answerable) | article | 97% | 100% | 0.985 |
| main | fixed | 94% | 100% | 0.967 |
| paraphrased (50) | article | 52% | 74% | 0.599 |
| paraphrased | fixed | 46% | 70% | 0.573 |

Article chunking wins on every ranking metric. It matters most at recall@1: the best
chunk is more often the whole answering article, so the LLM gets one clean source
instead of an article cut in two.

## Index: flat files, brute-force search

Each index is a folder of flat files in `data/index/<name>/`: `chunks.jsonl` (text
and metadata), `tokens.jsonl` (BM25 tokens), `embeddings.npy` (one normalised vector
per chunk) and `meta.json` (embedding model, dimensions, and a hash of the chunks the
vectors belong to). Two embedding backends exist: local `multilingual-e5-small` (384
dimensions, about an hour on CPU) and OpenAI `text-embedding-3-small` (`-oai`
indexes, 1536 dimensions, under 3 minutes and $0.14 for the article index). Dense
search is a single matrix product between the query vector and the embedding matrix,
followed by a top-k sort (`src/retrieve.py`). No vector database is used.

**Why this is enough.** The article index has 15,831 chunks. Even at 1536 dimensions
the embedding matrix is about 49 MB on disk, which fits in RAM many times over. An
exact cosine search over it takes milliseconds. That is negligible next to the
reranker (about 7 s per query on CPU) and the LLM call.

**What a vector database would add, and why we skip it.** A database such as FAISS,
Chroma, Qdrant or pgvector earns its keep through approximate nearest-neighbour
indexes (HNSW, IVF) once a collection reaches hundreds of thousands or millions of
vectors, plus filtering, updates and concurrent access at scale. Here:

- *Accuracy:* exact search is the upper bound that approximate indexes try to match,
  so a database could only tie or lose recall.
- *Latency:* the dense search is already a small share of the total. Speeding it up
  would not move p50 or p95 in a way users notice.
- *Operations:* a separate service to run, configure and deploy on a small CPU host
  (1-2 GB RAM) costs more than it gives. Flat files load at startup with numpy.
- *Filtering:* language and year filters are applied to the chunk metadata in Python
  before scoring, which is cheap at this size.
- *Updates:* the Journal Officiel corpus grows by a few laws a month, and rebuilding
  the index offline is acceptable. `meta.json` stores a hash of the chunks, so a
  rebuild reuses the embeddings when the chunks have not changed and only the
  expensive part is shared between machines (`scripts/pack_index.sh`).

**When to revisit.** Move to FAISS (in-process, no service) or pgvector if the corpus
grows past roughly 500k chunks, if dense search becomes a measurable share of latency,
or if the service needs live inserts without a rebuild.

## Retrieval: hybrid search, then rerank

- **BM25** (`rank-bm25`) over tokens normalised for both languages
  (`src/textnorm.py`). Arabic is NFKC-normalised, loses diacritics and tatweel, has
  alef/ya/ta-marbuta variants unified and the article prefixes (ال, وال, بال...)
  stripped. French loses its accents. Stopwords are removed in both. Keywords are strong here because questions often name a law
  or article number.
- **Vector search** over the embeddings above. It handles paraphrases and
  cross-language wording that BM25 misses.
- **Fusion** with reciprocal rank fusion (RRF, k = 60) over the top 30 of each. RRF
  uses ranks only, so the two score scales never need calibrating.
- **Rerank** the top 30 fused candidates with a multilingual cross-encoder
  (`mmarco-mMiniLMv2-L12-H384`) and keep 5.

What each step adds (main set, article chunking, e5): BM25 alone has 93% recall@5,
vectors alone 91%, hybrid 93%, and the reranker takes it to 100% (MRR 0.898 to
0.985). On paraphrased questions hybrid is below vector-only (58% vs 64%), since BM25
adds noise when the wording differs, and the reranker recovers it (74%). The reranker
is also by far the slowest step (about 7 s per query on CPU), which makes it the
Week 8 target (see `optimisation.md`).

## Generation

`src/generate.py` sends the 5 chunks, numbered `[1]`..`[5]`, with a system prompt
that requires a citation at the end of every sentence, the question's language, law
and article numbers copied exactly, and exactly "I don't know" / "لا أعرف" /
"Je ne sais pas" when the sources do not contain the answer. Generator:
`gpt-4o-mini` at temperature 0. Judge for the eval: `gpt-4.1-mini`. Citations are
parsed from the `[n]` markers and mapped back to chunks, so every claim links to a
law and article.

## Known failure cases

- **Tables.** Finance and budget-settlement laws are mostly tables that extract as
  loose lines of numbers. A chunk of such a table has no column headers, so questions
  about a specific budget line are unreliable.
- **Cross-references.** Many articles say "article 30 of law 2005-83 is replaced by
  ..." without restating it. Retrieval finds the amending article, but the answer can
  only be as complete as that article. The amended text is not merged in, and the
  corpus does not cover laws from before 2013.
- **Amendments and current law.** The corpus holds laws as published. If a later law
  changed an article, both versions are in the index, and the system may cite the
  older one. Answers are not legal advice.
- **Mislabelled source files.** The site sometimes serves the wrong PDF, and an
  Arabic file can contain the end of the previous law (41 mismatches logged). A chunk
  can then be cited under the wrong law number.
- **Arabic and French differ.** Article numbers in the two versions of an amending
  law can differ, and 37 laws exist only in Arabic and 45 only in French. A question
  in one language can need a source in the other. The prompt answers in the question's
  language from either.
- **Paraphrased questions.** Recall@5 drops from 100% to 74% when questions do not
  reuse the law's wording (`data/eval/qa_hard.jsonl`). This is the main remaining
  retrieval weakness.
- **Long articles.** An article over 1,200 characters is split, and the answer can
  sit across the cut. The 150-character overlap only partly covers this.
- **Gaps in coverage.** There are no laws from 2022, and nothing before 2013 (older
  PDFs use legacy font encodings). Questions about those years should get
  "I don't know".
