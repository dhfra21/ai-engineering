"""Retrieval eval: recall@k / MRR for each search mode, overall and per language.

  python -m eval.retrieval_eval [--strategy article] [--modes bm25 dense hybrid hybrid+rerank]
"""
import argparse
import json
import statistics
import time
from pathlib import Path

from eval.gold import is_gold, load_qa
from src.retrieve import MODES, Retriever

RESULTS = Path(__file__).resolve().parents[1] / "results"
KS = (1, 3, 5, 10)


def evaluate(retriever, items, mode, **search_kw):
    rows = []
    for it in items:
        t = time.perf_counter()
        hits = retriever.search(it["question"], mode=mode, k=max(KS), **search_kw)
        dt = time.perf_counter() - t
        rank = next((i + 1 for i, h in enumerate(hits) if is_gold(h, it)), None)
        rows.append({"id": it["id"], "lang": it["lang"], "rank": rank, "latency": dt})
    return rows


def summarise(rows):
    out = {"n": len(rows)}
    for k in KS:
        out[f"recall@{k}"] = sum(1 for r in rows if r["rank"] and r["rank"] <= k) / len(rows)
    out["mrr@10"] = sum(1 / r["rank"] for r in rows if r["rank"]) / len(rows)
    lat = sorted(r["latency"] for r in rows)
    out["search_p50_ms"] = 1000 * statistics.median(lat)
    out["search_p95_ms"] = 1000 * lat[int(0.95 * (len(lat) - 1))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strategy", default="article")
    ap.add_argument("--modes", nargs="+", default=list(MODES))
    a = ap.parse_args()
    items = load_qa(answerable_only=True)
    r = Retriever(a.strategy)
    # warm up models so load time is not counted as search latency
    for m in a.modes:
        r.search(items[0]["question"], mode=m, k=3)
    report = {}
    for mode in a.modes:
        rows = evaluate(r, items, mode)
        report[mode] = {"all": summarise(rows)}
        for lang in ("ar", "fr"):
            report[mode][lang] = summarise([x for x in rows if x["lang"] == lang])
        print(f"{mode:15s}", {k: round(v, 3) for k, v in report[mode]["all"].items()}, flush=True)
        (RESULTS / f"retrieval_{a.strategy}_{mode.replace('+', '_')}_rows.json").write_text(json.dumps(rows))
    (RESULTS / f"retrieval_{a.strategy}.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
