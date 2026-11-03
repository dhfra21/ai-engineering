import json

import numpy as np
import pytest

from src import embed, index
from src.chunking import Chunk


def test_parse_index_name():
    assert embed.parse_index_name("article") == ("article", "e5")
    assert embed.parse_index_name("fixed-oai") == ("fixed", "openai")
    with pytest.raises(KeyError):
        embed.parse_index_name("article-foo")


class FakeResp:
    status_code = 200

    def __init__(self, n, dims):
        self.n, self.dims = n, dims

    def raise_for_status(self):
        pass

    def json(self):
        rng = np.random.default_rng(0)
        return {"data": [{"index": i, "embedding": rng.normal(size=self.dims).tolist()} for i in reversed(range(self.n))],
                "usage": {"total_tokens": 1000 * self.n}}


def test_openai_embedder_normalises_and_prices(monkeypatch):
    monkeypatch.setattr(embed.config, "api_key", lambda: "k")
    seen = []
    monkeypatch.setattr(embed.httpx, "post", lambda url, json, **kw: seen.append(json) or FakeResp(len(json["input"]), 8))
    e = embed.OpenAIEmbedder(dims=8)
    vecs, usage = e.passages(["a", "b", "c"], batch=2)
    assert vecs.shape == (3, 8) and np.allclose(np.linalg.norm(vecs, axis=1), 1)
    assert usage["tokens"] == 3000 and usage["cost_usd"] == pytest.approx(3000 * 0.02 / 1e6)
    assert seen[0]["dimensions"] == 8 and len(seen) == 2          # batched, dimensions requested
    assert np.isclose(np.linalg.norm(e.query("q")), 1)


class CountingEmbedder:
    name, calls = "fake", 0

    def passages(self, texts, progress=None):
        CountingEmbedder.calls += 1
        return np.ones((len(texts), 4), dtype=np.float32) / 2, {"tokens": 10, "cost_usd": 0.5}


def test_existing_embeddings_are_reused_only_when_hash_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(index, "INDEX", tmp_path)
    chunks = [Chunk(f"d:fr:{i}", "d", "fr", 2020, 1, "Loi", "", f"texte {i}") for i in range(3)]
    monkeypatch.setattr(index, "load_chunks", lambda strategy, **kw: chunks)
    monkeypatch.setattr(index, "get_embedder", lambda backend, dims: CountingEmbedder())
    CountingEmbedder.calls = 0
    index.build("article-oai")
    index.build("article-oai")                       # same chunks: reuse
    assert CountingEmbedder.calls == 1
    meta = json.loads((tmp_path / "article-oai" / "meta.json").read_text())
    assert meta["backend"] == "openai" and meta["n_chunks"] == 3 and meta["embed_cost_usd"] == 0.5
    chunks[1] = Chunk("d:fr:1", "d", "fr", 2020, 1, "Loi", "", "texte modifié")
    index.build("article-oai")                       # chunk text changed: must re-embed
    assert CountingEmbedder.calls == 2
