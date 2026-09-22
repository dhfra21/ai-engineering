"""Does the judge agree with the humans? Runs the judge on every golden item
and compares its grade with the final human label.

    python -m harness.judge_eval --split dev --judge v1    # while improving the judge
    python -m harness.judge_eval --split test --judge v2   # the number you report

Writes results/judge/<judge-version>_<split>/{per_item.jsonl, summary.json, summary.md}.
The summary gives agreement (count, %, 95% CI), Cohen's kappa, the confusion
matrix, how many truly-bad answers the judge catches (recall of "bad"), a
breakdown by difficulty, by candidate source and by planted error type, the
judge's cost and latency per item, and every disagreement with the judge's
reason — the raw material for "where the judge fails".
"""
from __future__ import annotations

import argparse
import json

from harness import judge, prompts, stats
from harness.config import JUDGE_MODEL, MODELS, is_mock, results_root
from harness.data import load_golden, write_jsonl
from harness.llm import DailyLimitReached


def evaluate(golden: list[dict], judge_version: str, judge_model: str, use_cache: bool) -> list[dict]:
    rows = []
    for i, g in enumerate(golden, start=1):
        res = judge.grade(g, g["explanation"], judge_version, judge_model, use_cache=use_cache)
        rows.append({
            "item_id": g["id"], "split": g["split"], "difficulty": g["difficulty"],
            "source": g["source"],
            "error_type": (g["perturbation"] or {}).get("error_type"),
            "human": g["label"], "human_failed_criteria": g["failed_criteria"],
            "judge": res.data["grade"] if res.ok else None,
            "judge_failed_criteria": res.data["failed_criteria"] if res.ok else None,
            "judge_reason": res.data["reason"] if res.ok else None,
            "error": res.error,
            "tokens": [res.input_tokens, res.output_tokens],
            "latency_ms": res.latency_ms, "cost_usd": res.cost_usd,
        })
        agree = "  " if rows[-1]["judge"] == g["label"] else "XX"
        print(f"  [{i:3d}/{len(golden)}] {agree} {g['id']} human={g['label']:4s} judge={rows[-1]['judge']}")
    return rows


def slice_report(rows: list[dict], field: str) -> dict:
    out = {}
    for value in sorted({r[field] for r in rows if r[field] is not None}):
        s = [r for r in rows if r[field] == value]
        agree = sum(r["human"] == r["judge"] for r in s)
        bad = [r for r in s if r["human"] == "bad"]
        out[value] = {"agreement": stats.proportion(agree, len(s)),
                      "bad_caught": stats.proportion(sum(r["judge"] == "bad" for r in bad), len(bad))}
    return out


def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["judge"] is not None]
    lat = [r["latency_ms"] for r in rows]
    return {
        "n_items": len(rows),
        "judge_errors": len(rows) - len(ok),
        "human_vs_judge": stats.agreement_report([r["human"] for r in ok], [r["judge"] for r in ok]),
        "by_difficulty": slice_report(ok, "difficulty"),
        "by_source": slice_report(ok, "source"),
        "by_error_type": slice_report(ok, "error_type"),
        "cost_usd_per_item": round(sum(r["cost_usd"] for r in rows) / len(rows), 8) if rows else None,
        "latency_ms": {"p50": stats.percentile(lat, 50), "p95": stats.percentile(lat, 95)},
        "disagreements": [
            {k: r[k] for k in ("item_id", "source", "error_type", "human", "judge", "judge_reason")}
            for r in ok if r["human"] != r["judge"]
        ],
    }


def to_markdown(s: dict, title: str) -> str:
    h = s["human_vs_judge"]
    cm = h["confusion_rows_a_cols_b"]
    lines = [
        f"# Judge reliability — {title}",
        "",
        f"- Items: {s['n_items']} · judge call errors: {s['judge_errors']} (excluded below)",
        f"- **Agreement with humans: {stats.frac(h['agreement']['n'], h['agreement']['of'])}** "
        f"(95% CI {h['agreement']['ci95_pct']}%) · **Cohen's kappa {h['cohen_kappa']}** "
        f"({stats.kappa_words(h['cohen_kappa'])})",
        f"- Human-bad answers the judge also calls bad (recall): "
        f"{stats.frac(h['recall_of_bad']['n'], h['recall_of_bad']['of'])}",
        f"- Judge-bad answers humans agree are bad (precision): "
        f"{stats.frac(h['precision_of_bad']['n'], h['precision_of_bad']['of'])}",
        f"- Cost per judged item (list price): ${s['cost_usd_per_item']} · latency p50 "
        f"{s['latency_ms']['p50']} ms, p95 {s['latency_ms']['p95']} ms",
        "",
        "| human ↓ / judge → | good | bad |",
        "|---|---|---|",
        f"| good | {cm['good']['good']} | {cm['good']['bad']} |",
        f"| bad | {cm['bad']['good']} | {cm['bad']['bad']} |",
        "",
        "| Slice | Agreement | Human-bad caught |",
        "|---|---|---|",
    ]
    for key in ("by_difficulty", "by_source", "by_error_type"):
        for value, v in s[key].items():
            lines.append(f"| {key[3:]}={value} | {stats.frac(v['agreement']['n'], v['agreement']['of'])} "
                         f"| {stats.frac(v['bad_caught']['n'], v['bad_caught']['of'])} |")
    lines += ["", "## Disagreements", ""]
    for d in s["disagreements"]:
        tag = d["source"] + (f"/{d['error_type']}" if d["error_type"] else "")
        lines.append(f"- **{d['item_id']}** ({tag}) human={d['human']} judge={d['judge']}: {d['judge_reason']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--judge", default="v1")
    ap.add_argument("--judge-model", default=JUDGE_MODEL, choices=sorted(MODELS))
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    golden = load_golden(args.split)
    tag = prompts.load("judge", args.judge).tag
    print(f"Judge {tag} ({args.judge_model}) on {len(golden)} golden {args.split} items"
          f"{' [MOCK BACKEND]' if is_mock() else ''}")
    try:
        rows = evaluate(golden, args.judge, args.judge_model, use_cache=not args.no_cache)
    except DailyLimitReached as e:
        raise SystemExit(f"\nStopped: {e}")

    summary = summarize(rows)
    summary.update({"judge_prompt": tag, "judge_model": args.judge_model, "split": args.split})
    out_dir = results_root() / "judge" / f"{args.judge}_{args.judge_model}_{args.split}"
    write_jsonl(out_dir / "per_item.jsonl", rows)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = to_markdown(summary, f"{tag} on {args.judge_model}, {args.split} split")
    (out_dir / "summary.md").write_text(md, encoding="utf-8")
    print("\n" + md)
    print(f"-> {out_dir}")


if __name__ == "__main__":
    main()
