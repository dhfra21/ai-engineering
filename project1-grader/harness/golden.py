"""Merge two labellers into the golden set and measure how much they agree.

    python -m harness.golden --a alice --b bob

1. Reads data/labels/<a>.jsonl and data/labels/<b>.jsonl.
2. Reports agreement between the two (counts, %, Cohen's kappa, confusion
   matrix) -> results/labels/agreement.json and agreement.md. This number is
   computed on the RAW labels, before any discussion — it is the honest one.
3. Every item where they disagree (or either proposed a drop) goes into
   data/labels/adjudication.jsonl. Discuss each one, fill in "final"
   (good | bad | drop) and "reason", then rerun this command. Filled-in
   rows are kept across reruns.
4. Writes data/golden.jsonl: every item with a final label. Items still
   awaiting adjudication and dropped items are left out, and counted.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from harness import stats
from harness.config import GOLDEN_PATH, LABELS_DIR, RESULTS_DIR
from harness.data import load_candidates, load_queries, read_jsonl, write_jsonl

ADJ_PATH = LABELS_DIR / "adjudication.jsonl"


def latest_labels(name: str) -> dict[str, dict]:
    path = LABELS_DIR / f"{name}.jsonl"
    rows = read_jsonl(path)
    if not rows:
        raise SystemExit(f"No labels in {path}")
    return {r["item_id"]: r for r in rows}  # later rows win


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="first labeller's name")
    ap.add_argument("--b", required=True, help="second labeller's name")
    args = ap.parse_args()

    candidates = {c["id"]: c for c in load_candidates()}
    queries = {q["id"]: q for q in load_queries()}
    la, lb = latest_labels(args.a), latest_labels(args.b)
    both = [i for i in candidates if i in la and i in lb]
    only_one = [i for i in candidates if (i in la) != (i in lb)]
    neither = [i for i in candidates if i not in la and i not in lb]

    # ---- raw inter-annotator agreement (drop proposals excluded; counted separately)
    graded = [i for i in both if la[i]["grade"] != "drop" and lb[i]["grade"] != "drop"]
    ga = [la[i]["grade"] for i in graded]
    gb = [lb[i]["grade"] for i in graded]
    report = {
        "labellers": [args.a, args.b],
        "items_total": len(candidates),
        "labelled_by_both": len(both),
        "labelled_by_one_only": len(only_one),
        "labelled_by_neither": len(neither),
        "drop_proposed": {
            "by_both": sum(la[i]["grade"] == "drop" and lb[i]["grade"] == "drop" for i in both),
            "by_one": sum((la[i]["grade"] == "drop") != (lb[i]["grade"] == "drop") for i in both),
        },
        "grade_agreement": stats.agreement_report(ga, gb),
        "by_split": {},
        "by_difficulty": {},
        "by_source": {},
    }
    for field, key in (("split", "by_split"), ("difficulty", "by_difficulty"), ("source", "by_source")):
        for value in sorted({candidates[i][field] for i in graded}):
            ids = [i for i in graded if candidates[i][field] == value]
            a_, b_ = [la[i]["grade"] for i in ids], [lb[i]["grade"] for i in ids]
            k = stats.cohen_kappa(a_, b_)
            report[key][value] = {"agreement": stats.proportion(sum(x == y for x, y in zip(a_, b_)), len(ids)),
                                  "cohen_kappa": round(k, 3) if k is not None else None}
    both_bad = [i for i in graded if la[i]["grade"] == lb[i]["grade"] == "bad"]
    report["both_bad_same_criteria"] = stats.proportion(
        sum(set(la[i]["failed_criteria"]) == set(lb[i]["failed_criteria"]) for i in both_bad), len(both_bad))

    # ---- adjudication sheet
    existing = {r["item_id"]: r for r in read_jsonl(ADJ_PATH)}
    needs = [i for i in both if la[i]["grade"] != lb[i]["grade"] or "drop" in (la[i]["grade"], lb[i]["grade"])]
    needs = [i for i in needs if not (la[i]["grade"] == lb[i]["grade"] == "drop")]
    adj_rows = []
    for i in needs:
        prev = existing.get(i, {})
        adj_rows.append({
            "item_id": i,
            f"{args.a}": {k: la[i][k] for k in ("grade", "failed_criteria", "note")},
            f"{args.b}": {k: lb[i][k] for k in ("grade", "failed_criteria", "note")},
            "final": prev.get("final"),
            "final_failed_criteria": prev.get("final_failed_criteria", []),
            "reason": prev.get("reason", ""),
        })
    write_jsonl(ADJ_PATH, adj_rows)
    adj = {r["item_id"]: r for r in adj_rows}

    # ---- golden set
    golden, dropped, pending = [], [], []
    for i in both:
        a, b = la[i], lb[i]
        if a["grade"] == b["grade"] == "drop":
            dropped.append({"item_id": i, "reason": f"{a['note']} / {b['note']}", "how": "both labellers"})
            continue
        if i in adj:
            final = adj[i]["final"]
            if final not in ("good", "bad", "drop"):
                pending.append(i)
                continue
            if final == "drop":
                dropped.append({"item_id": i, "reason": adj[i]["reason"], "how": "adjudication"})
                continue
            crit = adj[i]["final_failed_criteria"] if final == "bad" else []
            adjudicated = True
        else:
            final = a["grade"]
            crit = sorted(set(a["failed_criteria"]) | set(b["failed_criteria"])) if final == "bad" else []
            adjudicated = False

        c = candidates[i]
        q = queries[c["query_id"]]
        golden.append({
            "id": i, "query_id": c["query_id"], "split": c["split"], "difficulty": c["difficulty"],
            "sql": q["sql"], "intent": q["intent"], "watch_for": q["watch_for"],
            "explanation": c["explanation"],
            "label": final, "failed_criteria": crit, "adjudicated": adjudicated,
            "label_a": a["grade"], "label_b": b["grade"],
            # analysis-only fields — never shown to the judge
            "source": c["source"], "perturbation": c["perturbation"],
            "alt_explanation": c["alt_explanation"], "alt_source": c["alt_source"],
        })
    write_jsonl(GOLDEN_PATH, golden)

    report["golden"] = {
        "items": len(golden),
        "label_counts": dict(Counter(g["label"] for g in golden)),
        "by_split": dict(Counter(g["split"] for g in golden)),
        "adjudicated": sum(g["adjudicated"] for g in golden),
        "pending_adjudication": pending,
        "dropped": dropped,
    }
    out_dir = RESULTS_DIR / "labels"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "agreement.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "agreement.md").write_text(to_markdown(report), encoding="utf-8")
    print(to_markdown(report))
    if pending:
        print(f"\n{len(pending)} items need adjudication: fill 'final' in {ADJ_PATH} and rerun.")


def to_markdown(r: dict) -> str:
    g = r["grade_agreement"]
    a, b = r["labellers"]
    cm = g["confusion_rows_a_cols_b"]
    lines = [
        f"# Inter-annotator agreement ({a} vs {b})",
        "",
        f"- Items: {r['items_total']} · labelled by both: {r['labelled_by_both']} · "
        f"by one only: {r['labelled_by_one_only']} · by neither: {r['labelled_by_neither']}",
        f"- Drop proposed by both: {r['drop_proposed']['by_both']} · by one: {r['drop_proposed']['by_one']}",
        f"- **Raw agreement on good/bad: {stats.frac(g['agreement']['n'], g['agreement']['of'])}** "
        f"(95% CI {g['agreement']['ci95_pct']}%)",
        f"- **Cohen's kappa: {g['cohen_kappa']}** ({stats.kappa_words(g['cohen_kappa'])})",
        f"- Both said bad and named the same failed criteria: "
        f"{stats.frac(r['both_bad_same_criteria']['n'], r['both_bad_same_criteria']['of'])}",
        "",
        f"| {a} ↓ / {b} → | good | bad |",
        "|---|---|---|",
        f"| good | {cm['good']['good']} | {cm['good']['bad']} |",
        f"| bad | {cm['bad']['good']} | {cm['bad']['bad']} |",
        "",
        "| Slice | Agreement | Kappa |",
        "|---|---|---|",
    ]
    for key in ("by_split", "by_difficulty", "by_source"):
        for value, s in r[key].items():
            lines.append(f"| {key[3:]}={value} | {stats.frac(s['agreement']['n'], s['agreement']['of'])} "
                         f"| {s['cohen_kappa']} |")
    gd = r["golden"]
    lines += [
        "",
        f"## Golden set: {gd['items']} items",
        f"- Labels: {gd['label_counts']} · split: {gd['by_split']} · resolved by adjudication: {gd['adjudicated']}",
        f"- Pending adjudication: {len(gd['pending_adjudication'])}",
        f"- Dropped: {len(gd['dropped'])}",
    ]
    for d in gd["dropped"]:
        lines.append(f"  - {d['item_id']} ({d['how']}): {d['reason']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
