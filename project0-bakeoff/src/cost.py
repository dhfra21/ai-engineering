"""Cost per 1k requests + latency p50/p95, from results/per_item.csv
(run score.py first so call errors are already flagged).

API models: cost = average real token usage (from the usage field of the
actual responses) x list price. Self-hosted model: hardware cost per hour
divided by requests per hour, where requests/hour is derived from the
measured average latency (one request at a time, matching how the eval
was run) — see results/hardware.json for the hourly rate you fill in
after running on your own machine.

Usage:
    python -m src.cost
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import MODEL_BY_KEY, RESULTS_DIR  # noqa: E402

ROOT = Path(__file__).parent.parent
PER_ITEM_PATH = ROOT / RESULTS_DIR / "per_item.csv"
HARDWARE_PATH = ROOT / RESULTS_DIR / "hardware.json"
OUT_PATH = ROOT / RESULTS_DIR / "cost_summary.csv"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def load_hardware() -> dict:
    if HARDWARE_PATH.exists():
        return json.loads(HARDWARE_PATH.read_text(encoding="utf-8"))
    return {"cost_per_hour_usd": None, "hardware": "UNSPECIFIED — fill in results/hardware.json"}


def main() -> None:
    with PER_ITEM_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_model[row["model_key"]].append(row)

    hardware = load_hardware()
    hw_cost_per_hour = hardware.get("cost_per_hour_usd")
    # "hardware" is a full multi-sentence description meant for the report;
    # take just the machine name for inline use in the break-even lines.
    hw_label = (hardware.get("hardware_short")
                or hardware.get("hardware", "open model").split(" — ")[0].strip())

    out_rows = []
    self_hosted_rph = None   # throughput ceiling of the self-hosted box, filled in below
    print(f"{'model':10s} {'p50 ms':>8s} {'p95 ms':>8s} {'cost/1k':>10s} {'note'}")

    for model_key, model_rows in by_model.items():
        spec = MODEL_BY_KEY[model_key]
        latencies = [float(r["latency_ms"]) for r in model_rows if r["latency_ms"]]
        p50 = percentile(latencies, 0.50)
        p95 = percentile(latencies, 0.95)

        note = ""
        if spec.kind != "ollama":
            # Any API-metered backend (groq, google, anthropic, ...) is
            # priced the same way: real token usage x list price. Only
            # "ollama" (self-hosted, no token pricing) takes the hardware
            # branch below — keying off that one kind instead of naming
            # every provider avoids silently mis-costing a model the next
            # time a provider gets swapped in or out.
            in_toks = [int(r["input_tokens"]) for r in model_rows if r["input_tokens"]]
            out_toks = [int(r["output_tokens"]) for r in model_rows if r["output_tokens"]]
            avg_in = mean(in_toks) if in_toks else 0
            avg_out = mean(out_toks) if out_toks else 0
            cost_per_request = (avg_in * spec.input_price_per_mtok
                                 + avg_out * spec.output_price_per_mtok) / 1_000_000
            cost_per_1k = cost_per_request * 1000
            cost_per_1k_100x = cost_per_1k  # flat: API pricing is per-token, no volume discount modeled
        else:
            tps = [float(r["tokens_per_second"]) for r in model_rows if r["tokens_per_second"]]
            avg_tps = mean(tps) if tps else None
            if hw_cost_per_hour is None or not latencies:
                cost_per_1k = None
                cost_per_1k_100x = None
                note = "set results/hardware.json cost_per_hour_usd to compute this"
            else:
                avg_latency_s = mean(latencies) / 1000
                requests_per_hour = 3600 / avg_latency_s
                self_hosted_rph = requests_per_hour
                cost_per_request = hw_cost_per_hour / requests_per_hour
                cost_per_1k = cost_per_request * 1000
                # At 100x traffic, a fixed-cost box already running has spare
                # cycles up to its real throughput ceiling — cost/1k could
                # fall toward this floor. Past that ceiling you need more
                # boxes and cost/1k goes flat again (same as today). Report
                # both; the two-page write-up should say which regime applies.
                cost_per_1k_100x = cost_per_1k  # conservative: same box, same rate
                note = f"avg {avg_tps:.1f} tok/s" if avg_tps else ""

        out_rows.append({
            "model_key": model_key,
            "model_id": spec.model_id,
            "role": spec.role,
            "p50_latency_ms": round(p50, 1) if latencies else None,
            "p95_latency_ms": round(p95, 1) if latencies else None,
            "cost_per_1k_requests_usd": round(cost_per_1k, 4) if cost_per_1k is not None else None,
            "cost_per_1k_requests_usd_at_100x": round(cost_per_1k_100x, 4) if cost_per_1k_100x is not None else None,
            "note": note,
        })
        cost_str = f"${cost_per_1k:.4f}" if cost_per_1k is not None else "N/A"
        print(f"{model_key:10s} {p50:8.0f} {p95:8.0f} {cost_str:>10s}  {note}")

    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"\nWrote {OUT_PATH}")

    # ---- break-even volume: API vs self-hosted ----
    api_rows = [r for r in out_rows if r["cost_per_1k_requests_usd"] is not None
                and MODEL_BY_KEY[r["model_key"]].kind != "ollama"]
    self_hosted = next((r for r in out_rows if MODEL_BY_KEY[r["model_key"]].kind == "ollama"), None)
    if self_hosted and hw_cost_per_hour and api_rows:
        print("\n--- break-even volume (requests/hour) vs. self-hosted ---")
        for r in api_rows:
            api_cost_per_request = r["cost_per_1k_requests_usd"] / 1000
            if api_cost_per_request > 0:
                breakeven = hw_cost_per_hour / api_cost_per_request
                print(f"  {r['model_key']} vs {self_hosted['model_key']}: "
                      f"break-even at ~{breakeven:.0f} requests/hour "
                      f"(above this, self-hosting on the {hw_label} is cheaper)")
        if self_hosted_rph:
            print(f"  ceiling: the {hw_label} sustains only ~{self_hosted_rph:.0f} requests/hour "
                  f"back-to-back, so self-hosting wins only between the break-even "
                  f"and that ceiling — above it you need more than one box.")
    else:
        print("\nSet results/hardware.json to compute the API-vs-self-hosted break-even volume.")


if __name__ == "__main__":
    main()
