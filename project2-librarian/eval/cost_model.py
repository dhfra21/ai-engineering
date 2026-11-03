"""Cost model: what one request costs, and what the service costs today and at 100x the traffic.

  python -m eval.cost_model                              # from results/generation_baseline.json
  python -m eval.cost_model --requests logs/requests.jsonl --label "preliminary"   # from service logs

Measured inputs: per-request generation cost and latency (generation eval rows or service logs), the index
build cost (data/index/<name>/meta.json) and the price table in src/config.py. Assumptions are arguments
with defaults, printed in the output so they can be challenged.
Writes results/cost_model.md.
"""
import argparse
import json
import math
import statistics
from pathlib import Path

from src import config

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load_rows(path):
    """Return [{'cost': usd, 'latency': seconds, 'abstained': bool}] from eval rows or service logs."""
    p = Path(path)
    if p.suffix == ".jsonl":                                    # service log
        rows = [json.loads(l) for l in p.open()]
        return [{"cost": r["usage"].get("cost_usd", 0.0), "latency": r["total_s"], "abstained": r["abstained"]} for r in rows]
    rows = json.loads(p.read_text())["rows"]                    # generation eval report
    return [{"cost": r["gen_cost"], "latency": r["latency"]["total"], "abstained": r["abstained"]} for r in rows]


def model(rows, index_meta, query_tokens=25, today_per_day=100, factor=100, utilisation=0.25,
          worker_usd_month=30.0, embed_price_per_m=0.02):
    gen = statistics.mean(r["cost"] for r in rows)
    embed = query_tokens * embed_price_per_m / 1e6 if index_meta.get("backend") == "openai" else 0.0
    per_request = gen + embed
    lat = sorted(r["latency"] for r in rows)
    p50, p95 = statistics.median(lat), lat[int(0.95 * (len(lat) - 1))]
    out = {"n_requests": len(rows), "gen_usd": gen, "embed_usd": embed, "per_request_usd": per_request,
           "latency_p50": p50, "latency_p95": p95, "index_build_usd": index_meta.get("embed_cost_usd", 0.0),
           "abstained_share": sum(r["abstained"] for r in rows) / len(rows), "scenarios": []}
    mean_latency = statistics.mean(lat)
    for name, per_day in (("today", today_per_day), (f"{factor}x", today_per_day * factor)):
        # one request occupies one worker for its whole latency (the reranker is CPU-bound)
        capacity = utilisation * 86400 / mean_latency
        workers = max(1, math.ceil(per_day / capacity))
        fees_month = per_request * per_day * 30
        out["scenarios"].append({"name": name, "per_day": per_day, "fees_month": fees_month, "workers": workers,
                                 "hosting_month": 0.0 if name == "today" else workers * worker_usd_month,
                                 "per_worker_per_day": capacity})
    return out


def to_markdown(m, label, params):
    s = [f"# Cost model ({label})", "",
         f"Measured on {m['n_requests']} requests; generator `{config.GENERATOR}`. Abstained: {100 * m['abstained_share']:.0f}%.", "",
         "| Item | Value |", "|---|---|",
         f"| Generation per request | ${m['gen_usd']:.5f} |",
         f"| Question embedding per request ({params['query_tokens']} tokens) | ${m['embed_usd']:.7f} |",
         f"| **Total per request** | **${m['per_request_usd']:.5f}** |",
         f"| Latency p50 / p95 | {m['latency_p50']:.1f} s / {m['latency_p95']:.1f} s |",
         f"| Index build, once | ${m['index_build_usd']:.3f} |", "",
         "| Scenario | Requests per day | Model fees per month | Workers needed | Hosting per month |", "|---|---|---|---|---|"]
    for sc in m["scenarios"]:
        host = "$0 (free CPU Space)" if sc["name"] == "today" else f"${sc['hosting_month']:.0f}"
        s.append(f"| {sc['name']} | {sc['per_day']:,} | ${sc['fees_month']:.2f} | {sc['workers']} | {host} |")
    s += ["", "**Assumptions** (change them with the options of `eval/cost_model.py`):",
          f"- today = {params['today_per_day']} requests per day (a class using it for a demo); 100x = {params['today_per_day'] * params['factor']:,}.",
          f"- one worker handles one request at a time for its whole latency (the reranker is CPU-bound), run at {int(100 * params['utilisation'])}% utilisation to leave headroom for peaks.",
          f"- a worker costs ${params['worker_usd_month']:.0f} per month (an assumed price for a small CPU VM, not a quote).",
          "- prices come from `src/config.py` (list prices); judge calls are an evaluation cost, not a serving cost.",
          "- hosting grows with the reranker's CPU time (5-9 s per request depending on the machine), while model fees are cents per thousand requests: that is why the reranker is the Week 8 target."]
    return "\n".join(s) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", default=str(RESULTS / "generation_baseline.json"), help="generation eval report (.json) or service log (.jsonl)")
    ap.add_argument("--index", default="article-oai")
    ap.add_argument("--label", default="from the generation baseline")
    ap.add_argument("--out", default=str(RESULTS / "cost_model.md"))
    ap.add_argument("--query-tokens", type=int, default=25)
    ap.add_argument("--today-per-day", type=int, default=100)
    ap.add_argument("--factor", type=int, default=100)
    ap.add_argument("--utilisation", type=float, default=0.25)
    ap.add_argument("--worker-usd-month", type=float, default=30.0)
    a = ap.parse_args()
    meta_f = ROOT / "data" / "index" / a.index / "meta.json"
    meta = json.loads(meta_f.read_text()) if meta_f.exists() else {}
    params = {k: getattr(a, k) for k in ("query_tokens", "today_per_day", "factor", "utilisation", "worker_usd_month")}
    m = model(load_rows(a.requests), meta, **params)
    text = to_markdown(m, a.label, params)
    Path(a.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
