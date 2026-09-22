"""THE harness command: run the system on a split, grade every answer with the
judge, write one row per item.

    python -m harness.run --split dev                     # system/v1, judge/v1
    python -m harness.run --split dev --system v2         # try a new prompt
    python -m harness.run --split test --system v3        # final report number only

Writes results/runs/<run_id>/
    per_item.jsonl  one row per query: input, output, score, reason, grade,
                    failed criteria, tokens, latency, cost, any error
    summary.json    counts + percentages overall, by difficulty, by failed
                    criterion; errors; cost; latency
and appends one line to results/history.csv. If an earlier run exists on the
same split with the same judge, prints the change and exactly which items
flipped — that is what goes into prompts/CHANGELOG.md.

Rules (LABELLING_GUIDE.md §5): tune prompts on dev only. Run test once per
version you intend to report, never to pick between versions.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone

from harness import judge, prompts, stats, system
from harness.config import JUDGE_MODEL, MODELS, SYSTEM_MODEL, is_mock, results_root
from harness.data import load_queries, read_jsonl, write_jsonl
from harness.llm import DailyLimitReached
from harness.schemas import CRITERIA

HISTORY_FIELDS = ["run_id", "finished_at", "split", "n_items", "system_prompt", "system_sha",
                  "system_model", "judge_prompt", "judge_sha", "judge_model", "good", "bad",
                  "errors", "pct_good", "cost_usd_total", "note"]


def run(split: str, system_version: str, judge_version: str, system_model: str, judge_model: str,
        limit: int | None, use_cache: bool) -> list[dict]:
    queries = load_queries(split)[:limit] if limit else load_queries(split)
    sys_prompt = prompts.load("system", system_version)
    jdg_prompt = prompts.load("judge", judge_version)
    rows = []
    for i, q in enumerate(queries, start=1):
        out = system.explain(q["sql"], system_version, system_model, use_cache=use_cache)
        row = {
            "item_id": q["id"], "split": q["split"], "difficulty": q["difficulty"],
            "input": q["sql"],
            "output": out.data["explanation"] if out.ok else None,
            "score": None, "grade": None, "reason": None, "failed_criteria": None,
            "error": None,
            "system_prompt": sys_prompt.tag, "system_sha": sys_prompt.sha, "system_model": system_model,
            "judge_prompt": jdg_prompt.tag, "judge_sha": jdg_prompt.sha, "judge_model": judge_model,
            "system_tokens": [out.input_tokens, out.output_tokens],
            "system_latency_ms": out.latency_ms, "system_cost_usd": out.cost_usd,
            "judge_tokens": None, "judge_latency_ms": None, "judge_cost_usd": 0.0,
        }
        if not out.ok:
            row["error"] = f"system: {out.error}"
        else:
            verdict = judge.grade(q, row["output"], judge_version, judge_model, use_cache=use_cache)
            row.update({
                "judge_tokens": [verdict.input_tokens, verdict.output_tokens],
                "judge_latency_ms": verdict.latency_ms, "judge_cost_usd": verdict.cost_usd,
            })
            if verdict.ok:
                row.update({"score": judge.score_of(verdict), "grade": verdict.data["grade"],
                            "reason": verdict.data["reason"],
                            "failed_criteria": verdict.data["failed_criteria"]})
            else:
                row["error"] = f"judge: {verdict.error}"
        mark = {1: "good", 0: "BAD ", None: "ERR "}[row["score"]]
        print(f"  [{i:3d}/{len(queries)}] {q['id']} {q['difficulty']:6s} {mark} "
              f"{(row['reason'] or row['error'] or '')[:90]}")
        rows.append(row)
    return rows


def summarize(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["score"] is not None]
    good = sum(r["score"] for r in scored)
    by_diff = {}
    for d in ("easy", "medium", "hard"):
        s = [r for r in scored if r["difficulty"] == d]
        by_diff[d] = stats.proportion(sum(r["score"] for r in s), len(s))
    crit = Counter(c for r in scored for c in (r["failed_criteria"] or []))
    sys_lat = [r["system_latency_ms"] for r in rows]
    jdg_lat = [r["judge_latency_ms"] for r in rows]
    cost_sys = sum(r["system_cost_usd"] for r in rows)
    cost_jdg = sum(r["judge_cost_usd"] for r in rows)
    return {
        "n_items": len(rows),
        "scored": len(scored),
        "good": stats.proportion(good, len(scored)),
        "bad": stats.proportion(len(scored) - good, len(scored)),
        "errors": {"system": sum(1 for r in rows if (r["error"] or "").startswith("system")),
                   "judge": sum(1 for r in rows if (r["error"] or "").startswith("judge"))},
        "by_difficulty": by_diff,
        "failed_criteria_counts": {c: crit.get(c, 0) for c in CRITERIA},
        "cost_usd": {"system_total": round(cost_sys, 6), "judge_total": round(cost_jdg, 6),
                     "system_per_item": round(cost_sys / len(rows), 8) if rows else None,
                     "judge_per_item": round(cost_jdg / len(rows), 8) if rows else None},
        "latency_ms": {"system_p50": stats.percentile(sys_lat, 50), "system_p95": stats.percentile(sys_lat, 95),
                       "judge_p50": stats.percentile(jdg_lat, 50), "judge_p95": stats.percentile(jdg_lat, 95)},
    }


def compare_with_previous(history: list[dict], current: dict, rows: list[dict]) -> str | None:
    prev = [h for h in history if h["split"] == current["split"] and h["judge_sha"] == current["judge_sha"]
            and h["system_model"] == current["system_model"] and h["run_id"] != current["run_id"]]
    if not prev:
        return None
    p = prev[-1]
    prev_rows = {r["item_id"]: r for r in read_jsonl(results_root() / "runs" / p["run_id"] / "per_item.jsonl")}
    up = [r["item_id"] for r in rows if r["score"] == 1 and prev_rows.get(r["item_id"], {}).get("score") == 0]
    down = [r["item_id"] for r in rows if r["score"] == 0 and prev_rows.get(r["item_id"], {}).get("score") == 1]
    return (f"vs previous run {p['run_id']} ({p['system_prompt']}): "
            f"good {p['good']}/{int(p['good']) + int(p['bad'])} ({p['pct_good']}%) -> "
            f"{current['good']}/{current['good'] + current['bad']} ({current['pct_good']}%)\n"
            f"  bad->good ({len(up)}): {', '.join(up) or '-'}\n"
            f"  good->bad ({len(down)}): {', '.join(down) or '-'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--system", default="v1", help="prompts/system/<version>.md")
    ap.add_argument("--judge", default="v1", help="prompts/judge/<version>.md")
    ap.add_argument("--system-model", default=SYSTEM_MODEL, choices=sorted(MODELS))
    ap.add_argument("--judge-model", default=JUDGE_MODEL, choices=sorted(MODELS))
    ap.add_argument("--limit", type=int, help="only the first N items (smoke test; not for reporting)")
    ap.add_argument("--no-cache", action="store_true", help="force fresh API calls")
    ap.add_argument("--note", default="", help="free text stored in history.csv")
    args = ap.parse_args()

    print(f"Running system/{args.system} ({args.system_model}) + judge/{args.judge} "
          f"({args.judge_model}) on {args.split}{' [MOCK BACKEND]' if is_mock() else ''}")
    try:
        rows = run(args.split, args.system, args.judge, args.system_model, args.judge_model,
                   args.limit, use_cache=not args.no_cache)
    except DailyLimitReached as e:
        raise SystemExit(f"\nStopped: {e}\nNothing written for this run.")

    finished = datetime.now(timezone.utc)
    base_id = (f"{finished:%Y%m%d-%H%M%S}_{args.split}_sys-{args.system}_judge-{args.judge}"
               + (f"_limit{args.limit}" if args.limit else ""))
    run_id, n = base_id, 1
    while (results_root() / "runs" / run_id).exists():  # never overwrite an earlier run
        n += 1
        run_id = f"{base_id}_{n}"
    out_dir = results_root() / "runs" / run_id
    summary = summarize(rows)
    summary.update({"run_id": run_id, "split": args.split, "system_prompt": rows[0]["system_prompt"],
                    "system_sha": rows[0]["system_sha"], "system_model": args.system_model,
                    "judge_prompt": rows[0]["judge_prompt"], "judge_sha": rows[0]["judge_sha"],
                    "judge_model": args.judge_model, "limit": args.limit, "note": args.note})
    write_jsonl(out_dir / "per_item.jsonl", rows)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    hist_path = results_root() / "history.csv"
    history = []
    if hist_path.exists():
        with hist_path.open(encoding="utf-8") as f:
            history = list(csv.DictReader(f))
    line = {
        "run_id": run_id, "finished_at": finished.isoformat(timespec="seconds"), "split": args.split,
        "n_items": len(rows), "system_prompt": summary["system_prompt"], "system_sha": summary["system_sha"],
        "system_model": args.system_model, "judge_prompt": summary["judge_prompt"],
        "judge_sha": summary["judge_sha"], "judge_model": args.judge_model,
        "good": summary["good"]["n"], "bad": summary["bad"]["n"],
        "errors": summary["errors"]["system"] + summary["errors"]["judge"],
        "pct_good": summary["good"]["pct"], "cost_usd_total": round(
            summary["cost_usd"]["system_total"] + summary["cost_usd"]["judge_total"], 6),
        "note": args.note,
    }
    if not args.limit:  # smoke tests never enter the history the changelog is built from
        new_file = not hist_path.exists()
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        with hist_path.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
            if new_file:
                w.writeheader()
            w.writerow(line)

    s = summary
    print(f"\n=== {run_id}")
    print(f"good: {stats.frac(s['good']['n'], s['scored'])}  95% CI {s['good']['ci95_pct']}%   "
          f"errors: system={s['errors']['system']} judge={s['errors']['judge']} (not scored)")
    for d, p in s["by_difficulty"].items():
        print(f"  {d:6s} {stats.frac(p['n'], p['of'])}")
    print(f"failed criteria (an item can fail several): {s['failed_criteria_counts']}")
    print(f"cost: system ${s['cost_usd']['system_total']:.4f}, judge ${s['cost_usd']['judge_total']:.4f} "
          f"(list price)   latency p50 system {s['latency_ms']['system_p50']} ms, judge {s['latency_ms']['judge_p50']} ms")
    delta = compare_with_previous(history, line, rows)
    if delta:
        print(delta)
    print(f"-> {out_dir}")


if __name__ == "__main__":
    main()
