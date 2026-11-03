"""Embedding backends for the dense index.

  e5      local multilingual-e5-small (CPU, ~1 hour for the whole corpus, no API cost)
  openai  text-embedding-3-small through the API (minutes, about $0.1 for the corpus)

An index name selects one: "article" is chunking=article with e5, "article-oai" is
chunking=article with OpenAI embeddings. Queries must be embedded with the model the index
was built with, so the backend is stored in the index's meta.json.
"""
import time

import httpx
import numpy as np

from . import config

E5_MODEL = "intfloat/multilingual-e5-small"
OPENAI_MODEL = "text-embedding-3-small"
OPENAI_URL = "https://api.openai.com/v1/embeddings"
EMBED_PRICES = {OPENAI_MODEL: 0.02, "text-embedding-3-large": 0.13}  # USD per million tokens


def parse_index_name(name):
    """'article' -> ('article', 'e5'); 'article-oai' -> ('article', 'openai')."""
    strategy, _, suffix = name.partition("-")
    return strategy, {"": "e5", "oai": "openai"}[suffix]


class E5:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(E5_MODEL)
        self.model.max_seq_length = 384
        self.name, self.dims = E5_MODEL, 384

    def passages(self, texts, progress=None):
        parts = []
        for start in range(0, len(texts), 1024):
            parts.append(self.model.encode(["passage: " + t for t in texts[start:start + 1024]], batch_size=32,
                                           normalize_embeddings=True, show_progress_bar=False))
            if progress:
                progress(min(start + 1024, len(texts)), len(texts))
        return np.concatenate(parts), {"tokens": None, "cost_usd": 0.0}

    def query(self, text):
        return self.model.encode(["query: " + text], normalize_embeddings=True)[0]


class OpenAIEmbedder:
    def __init__(self, model=OPENAI_MODEL, dims=None):
        self.name, self.dims = model, dims or 1536

    def _post(self, texts, retries=5):
        body = {"model": self.name, "input": texts}
        if self.dims != 1536:
            body["dimensions"] = self.dims
        for attempt in range(retries):
            r = httpx.post(OPENAI_URL, json=body, timeout=120, headers={"Authorization": f"Bearer {config.api_key()}"})
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            d = r.json()
            vecs = np.array([x["embedding"] for x in sorted(d["data"], key=lambda x: x["index"])], dtype=np.float32)
            return vecs, d["usage"]["total_tokens"]
        raise RuntimeError("embeddings API failed after retries")

    def passages(self, texts, progress=None, batch=128):
        parts, tokens = [], 0
        for start in range(0, len(texts), batch):
            v, t = self._post(texts[start:start + batch])
            parts.append(v)
            tokens += t
            if progress:
                progress(min(start + batch, len(texts)), len(texts))
        vecs = np.concatenate(parts)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)  # truncated dimensions are not unit length
        return vecs, {"tokens": tokens, "cost_usd": tokens * EMBED_PRICES.get(self.name, 0.0) / 1e6}

    def query(self, text):
        v, _ = self._post([text])
        return v[0] / np.linalg.norm(v[0])


def get_embedder(backend, dims=None):
    return E5() if backend == "e5" else OpenAIEmbedder(dims=dims)
