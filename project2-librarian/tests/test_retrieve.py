"""Retriever logic with a tiny hand-made index (no models loaded)."""
import numpy as np

from src.retrieve import Retriever
from src.textnorm import tokenize
from rank_bm25 import BM25Okapi

DOCS = [
    ("law-1-1", "fr", "Le délai de recours est de sept jours."),
    ("law-2-1", "fr", "Le salaire est payé une fois par mois."),
    ("law-3-1", "ar", "يدفع الأجر مرة في الشهر."),
]


class FakeReranker:
    calls = 0

    def predict(self, pairs):
        FakeReranker.calls += 1
        return [float(len(p[1])) for p in pairs]


def make():
    r = Retriever.__new__(Retriever)
    r.chunks = [{"id": f"{d}:{l}:0", "doc_id": d, "lang": l, "year": 2000 + i, "article": "Art. 1", "text": t}
                for i, (d, l, t) in enumerate(DOCS)]
    r.bm25 = BM25Okapi([tokenize(c["text"]) for c in r.chunks])
    r.vecs = np.eye(3, dtype=np.float32)
    r._embedder = None
    r._reranker = FakeReranker()
    r.rerank_max_length = 384
    r.dense_search = lambda q, n: (np.array([1, 0, 2]), np.array([.9, .5, .1]))  # dense prefers the salary law
    return r


def test_bm25_finds_lexical_match():
    assert make().search("délai de recours", mode="bm25", k=1)[0]["doc_id"] == "law-1-1"


def test_language_filter():
    hits = make().search("salaire", mode="bm25", k=3, lang="ar")
    assert all(h["lang"] == "ar" for h in hits)


def test_rerank_is_skipped_when_first_search_is_confident():
    r = make()
    FakeReranker.calls = 0
    r.search("délai de recours", mode="hybrid+rerank", k=2)
    assert FakeReranker.calls == 1
    r.search("délai de recours", mode="hybrid+rerank", k=2, skip_rerank_gap=0.0)  # any gap counts as confident
    assert FakeReranker.calls == 1


def test_hybrid_fuses_both_rankings():
    hits = make().search("salaire par mois", mode="hybrid", k=3)
    assert len(hits) == 3
    assert hits[0]["doc_id"] == "law-2-1"  # lexical and dense signals both point to the salary law
    assert hits[0]["score"] > hits[-1]["score"]
