"""Search latency of several reranker settings, interleaved per question.

  python -m eval.latency_bench [--set qa] [--configs 30x384 10x384 10x256] [--gen results/generation_w8b_0_tuned.json]

Running one configuration after another is unfair on a laptop whose CPU speed changes during a run (we saw search
time switch between 1.5 s and 5 s mid-run). Here every question is searched with every configuration back to back,
in rotating order, so a slow phase hits all of them alike. End-to-end latency per question is that search time plus
the generation time measured for the same question in a full eval run (`--gen`): generation is an API call that
does not depend on the reranker setting.
"""
import argparse
import json
import statistics
import time
from pathlib import Path

from eval.gold import load_qa
from src.retrieve import Retriever

RESULTS = Path(__file__).resolve().parents[1] / "results"


def pct(xs, q):
    xs = sorted(xs)
    return xs[int(q * (len(xs) - 1))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="qa")
    ap.add_argument("--strategy", default="article-oai")
    ap.add_argument("--configs", nargs="+", default=["30x384", "10x384", "10x256"], help="<candidates>x<rerank tokens>")
    ap.add_argument("--gen", default=str(RESULTS / "generation_w8b_0_tuned.json"), help="eval run to take generation times from")
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    configs = [tuple(int(v) for v in c.split("x")) for c in a.configs]
    base = Retriever(a.strategy)
    by_length = {}
    for _, length in configs:   # one retriever per rerank length, sharing the index and the query embedder
        if length not in by_length:
            r = Retriever.__new__(Retriever)
            r.__dict__.update(base.__dict__)
            r.rerank_max_length, r._reranker = length, None
            by_length[length] = r
    retrievers = {(n, length): by_length[length] for n, length in configs}
    items = load_qa(name=a.set)
    gen = {row["id"]: row["latency"]["generate"] for row in json.loads(Path(a.gen).read_text(encoding="utf-8"))["rows"]}
    for (n, _), r in retrievers.items():   # load models before timing
        r.search(items[0]["question"], k=a.k, n_candidates=n)
    search = {c: {} for c in configs}
    for i, it in enumerate(items):
        order = configs[i % len(configs):] + configs[: i % len(configs)]
        for c in order:
            t = time.perf_counter()
            retrievers[c].search(it["question"], k=a.k, n_candidates=c[0])
            search[c][it["id"]] = time.perf_counter() - t
        print(f"{i + 1}/{len(items)} " + " ".join(f"{n}x{l}={search[(n, l)][it['id']]:.2f}" for n, l in configs), flush=True)
    report = {"set": a.set, "gen_from": a.gen, "configs": {}}
    for n, length in configs:
        s = search[(n, length)]
        total = [s[q] + gen.get(q, 0.0) for q in s]
        report["configs"][f"{n}x{length}"] = {
            "search_p50_s": statistics.median(s.values()), "search_p95_s": pct(s.values(), 0.95),
            "total_p50_s": statistics.median(total), "total_p95_s": pct(total, 0.95)}
    (RESULTS / f"latency_bench_{a.set}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report["configs"], indent=1))


if __name__ == "__main__":
    main()
