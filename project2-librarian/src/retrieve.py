"""Hybrid retrieval: BM25 + dense vectors fused with RRF, then a cross-encoder rerank."""
import json
import time
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Okapi

from .index import EMBED_MODEL, index_dir
from .textnorm import tokenize

RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
MODES = ("bm25", "dense", "hybrid", "hybrid+rerank")


class Retriever:
    def __init__(self, strategy="article"):
        d = index_dir(strategy)
        self.chunks = [json.loads(l) for l in (d / "chunks.jsonl").open()]
        self.bm25 = BM25Okapi([json.loads(l) for l in (d / "tokens.jsonl").open()])
        self.vecs = np.load(d / "embeddings.npy").astype(np.float32)
        self._embedder = self._reranker = None

    @property
    def embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(EMBED_MODEL)
        return self._embedder

    @property
    def reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(RERANK_MODEL, max_length=384)
        return self._reranker

    # each returns (chunk indices, scores) best first
    def bm25_search(self, query, n):
        s = self.bm25.get_scores(tokenize(query))
        idx = np.argsort(-s)[:n]
        return idx, s[idx]

    def dense_search(self, query, n):
        q = self.embedder.encode(["query: " + query], normalize_embeddings=True)[0]
        s = self.vecs @ q
        idx = np.argsort(-s)[:n]
        return idx, s[idx]

    def search(self, query, mode="hybrid+rerank", k=5, n_candidates=30, rrf_k=60, lang=None, year=None):
        """Return the top-k chunks (dicts with a 'score'). lang/year are metadata filters."""
        def allowed(i):
            c = self.chunks[i]
            return (lang is None or c["lang"] == lang) and (year is None or c["year"] == year)

        pool = n_candidates * (1 if lang is None and year is None else 5)
        if mode == "bm25":
            idx, sc = self.bm25_search(query, pool)
            ranked = [(i, s) for i, s in zip(idx, sc) if allowed(i)]
        elif mode == "dense":
            idx, sc = self.dense_search(query, pool)
            ranked = [(i, s) for i, s in zip(idx, sc) if allowed(i)]
        else:
            fused = {}
            for idx, _ in (self.bm25_search(query, pool), self.dense_search(query, pool)):
                for rank, i in enumerate(idx):
                    if allowed(i):
                        fused[i] = fused.get(i, 0) + 1 / (rrf_k + rank + 1)
            ranked = sorted(fused.items(), key=lambda x: -x[1])
            if mode == "hybrid+rerank":
                cand = [i for i, _ in ranked[:n_candidates]]
                scores = self.reranker.predict([(query, self.chunks[i]["text"]) for i in cand])
                ranked = sorted(zip(cand, scores), key=lambda x: -x[1])
        return [{**self.chunks[i], "score": float(s)} for i, s in ranked[:k]]


@lru_cache(maxsize=1)
def get_retriever(strategy="article"):
    return Retriever(strategy)
