"""Cost model from real token usage in a finished run.

    python -m harness.cost                          # latest non-mock run in history.csv
    python -m harness.cost --run <run_id> --daily-requests 2000 --judge-sample 0.05

Uses the measured tokens per item (system and judge) x Groq's published paid
price (harness/config.py). Reports:
  - cost per 1,000 requests: system alone, and system + judge
  - monthly cost at today's traffic and at 100x, where "traffic" is the
    --daily-requests assumption and the judge grades a --judge-sample
    fraction of production answers (monitoring), not all of them
  - whether that traffic fits Groq's free tier (1,000 requests/day/model)

The daily-traffic number is an assumption — state it in the report.
"""
from __future__ import annotations

import argparse
import csv
import json

from harness import stats
from harness.config import MODELS, results_root
from harness.data import read_jsonl

FREE_TIER_RPD = 1000


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", help="run_id under results/runs/ (default: latest in history.csv)")
    ap.add_argument("--daily-requests", type=int, default=500, help="assumed production traffic today")
    ap.add_argument("--judge-sample", type=float, default=0.10,
                    help="fraction of production answers the judge grades for monitoring")
    args = ap.parse_args()

    root = results_root()
    run_id = args.run
    if not run_id:
        with (root / "history.csv").open(encoding="utf-8") as f:
            run_id = list(csv.DictReader(f))[-1]["run_id"]
    rows = read_jsonl(root / "runs" / run_id / "per_item.jsonl")
    if not rows:
        raise SystemExit(f"No per_item.jsonl for run {run_id}")

    n = len(rows)
    sys_cost = sum(r["system_cost_usd"] for r in rows) / n
    judged = [r for r in rows if r["judge_tokens"]]
    jdg_cost = sum(r["judge_cost_usd"] for r in judged) / len(judged) if judged else 0.0
    sys_in = sum(r["system_tokens"][0] for r in rows) / n
    sys_out = sum(r["system_tokens"][1] for r in rows) / n
    jdg_in = sum(r["judge_tokens"][0] for r in judged) / max(len(judged), 1)
    jdg_out = sum(r["judge_tokens"][1] for r in judged) / max(len(judged), 1)

    def monthly(daily: int) -> dict:
        system_m = daily * 30 * sys_cost
        judge_m = daily * 30 * args.judge_sample * jdg_cost
        return {"daily_requests": daily, "system_usd": round(system_m, 2), "judge_usd": round(judge_m, 2),
                "total_usd": round(system_m + judge_m, 2),
                "fits_free_tier": daily <= FREE_TIER_RPD and daily * args.judge_sample <= FREE_TIER_RPD}

    sys_model = MODELS[rows[0]["system_model"]]
    jdg_model = MODELS[rows[0]["judge_model"]]
    report = {
        "run_id": run_id,
        "system": {"model": sys_model.model_id, "avg_input_tokens": round(sys_in, 1),
                   "avg_output_tokens": round(sys_out, 1), "usd_per_request": round(sys_cost, 8),
                   "latency_ms_p50": stats.percentile([r["system_latency_ms"] for r in rows], 50),
                   "latency_ms_p95": stats.percentile([r["system_latency_ms"] for r in rows], 95)},
        "judge": {"model": jdg_model.model_id, "avg_input_tokens": round(jdg_in, 1),
                  "avg_output_tokens": round(jdg_out, 1), "usd_per_judged_item": round(jdg_cost, 8),
                  "latency_ms_p50": stats.percentile([r["judge_latency_ms"] for r in judged], 50),
                  "latency_ms_p95": stats.percentile([r["judge_latency_ms"] for r in judged], 95)},
        "per_1k_requests_usd": {"system_only": round(1000 * sys_cost, 4),
                                "system_plus_judge_every_answer": round(1000 * (sys_cost + jdg_cost), 4),
                                f"system_plus_judge_{args.judge_sample:.0%}_sample":
                                    round(1000 * (sys_cost + args.judge_sample * jdg_cost), 4)},
        "monthly_today": monthly(args.daily_requests),
        "monthly_at_100x": monthly(args.daily_requests * 100),
        "assumptions": {"daily_requests_today": args.daily_requests, "judge_sample": args.judge_sample,
                        "prices": "Groq paid list price, see harness/config.py", "days_per_month": 30,
                        "note": "output tokens include gpt-oss reasoning tokens, which are billed"},
    }
    out = root / "cost" / f"{run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
