"""Build the search index: BM25 tokens + dense embeddings, stored as flat files.

Flat files (numpy + jsonl) are enough here: ~10k chunks, so brute-force cosine
search is a matrix product that takes a few ms; a vector database would add
a service to run and nothing to accuracy at this size.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

from .chunking import load_chunks
from .textnorm import tokenize

INDEX = Path(__file__).resolve().parents[1] / "data" / "index"
EMBED_MODEL = "intfloat/multilingual-e5-small"


def index_dir(strategy):
    return INDEX / strategy


def build(strategy="article", **chunk_kw):
    from dataclasses import asdict
    from sentence_transformers import SentenceTransformer

    out = index_dir(strategy)
    out.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks(strategy, **chunk_kw)
    print(f"{len(chunks)} chunks", flush=True)
    with (out / "chunks.jsonl").open("w") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    with (out / "tokens.jsonl").open("w") as f:
        for c in chunks:
            f.write(json.dumps(tokenize(c.text), ensure_ascii=False) + "\n")
    model = SentenceTransformer(EMBED_MODEL)
    model.max_seq_length = 384
    t = time.time()
    # sort by length so batches pad little
    order = np.argsort([len(c.text) for c in chunks])
    embs = model.encode(["passage: " + chunks[i].text for i in order], batch_size=32,
                        normalize_embeddings=True, show_progress_bar=False)
    vecs = np.zeros_like(embs)
    vecs[order] = embs
    np.save(out / "embeddings.npy", vecs.astype(np.float16))
    print(f"embedded in {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "article")
