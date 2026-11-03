"""Build the search index: BM25 tokens + dense embeddings, stored as flat files.

Flat files (numpy + jsonl) are enough here: ~16k chunks, so brute-force cosine search is a
matrix product that takes a few ms; a vector database would add a service to run and nothing
to accuracy at this size.

  python -m src.index article          # chunking=article, local e5 embeddings (~1 h on CPU)
  python -m src.index article-oai      # chunking=article, OpenAI embeddings (minutes)
  python -m src.index article-oai --dims 512   # smaller vectors (cheaper, smaller index)

chunks.jsonl and tokens.jsonl are rebuilt from the corpus in under a minute. embeddings.npy is
the slow/expensive part, so if one already exists whose meta.json matches the chunks (same hash),
it is reused: download it from the release asset instead of re-embedding.
"""
import argparse
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .chunking import load_chunks
from .embed import get_embedder, parse_index_name
from .textnorm import tokenize

INDEX = Path(__file__).resolve().parents[1] / "data" / "index"


def index_dir(name):
    return INDEX / name


def chunks_hash(chunks):
    h = hashlib.sha256()
    for c in chunks:
        h.update(c.id.encode())
        h.update(c.text.encode())
    return h.hexdigest()


def build(name="article", dims=None, **chunk_kw):
    strategy, backend = parse_index_name(name)
    out = index_dir(name)
    out.mkdir(parents=True, exist_ok=True)
    chunks = load_chunks(strategy, **chunk_kw)
    digest = chunks_hash(chunks)
    print(f"{len(chunks)} chunks, hash {digest[:12]}", flush=True)
    with (out / "chunks.jsonl").open("w") as f:
        for c in chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
    with (out / "tokens.jsonl").open("w") as f:
        for c in chunks:
            f.write(json.dumps(tokenize(c.text), ensure_ascii=False) + "\n")

    meta_path, emb_path = out / "meta.json", out / "embeddings.npy"
    if meta_path.exists() and emb_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("chunks_hash") == digest and meta.get("n_chunks") == len(chunks):
            print("embeddings.npy matches these chunks: reusing it (no embedding cost).", flush=True)
            return
        print("embeddings.npy does not match these chunks: re-embedding.", flush=True)

    emb = get_embedder(backend, dims)
    t = time.time()
    order = np.argsort([len(c.text) for c in chunks])  # sort by length so batches pad little (e5)
    vecs, usage = emb.passages([chunks[i].text for i in order],
                               progress=lambda d, n: print(f"  embedded {d}/{n} ({time.time() - t:.0f}s)", flush=True))
    out_vecs = np.zeros_like(vecs)
    out_vecs[order] = vecs
    np.save(emb_path, out_vecs.astype(np.float16))
    meta_path.write_text(json.dumps({
        "backend": backend, "model": emb.name, "dims": int(out_vecs.shape[1]), "n_chunks": len(chunks),
        "chunks_hash": digest, "embed_seconds": round(time.time() - t, 1),
        "embed_tokens": usage["tokens"], "embed_cost_usd": usage["cost_usd"]}, indent=1))
    print(f"embedded in {time.time() - t:.0f}s, {usage}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name", nargs="?", default="article", help="article | fixed | article-oai | fixed-oai")
    ap.add_argument("--dims", type=int, default=None, help="OpenAI embedding dimensions (default 1536)")
    a = ap.parse_args()
    build(a.name, a.dims)
