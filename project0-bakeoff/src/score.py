"""Score results/per_item.csv (produced by run.py) by execution accuracy:
run each model's generated SQL and the gold SQL against the same
read-only database, compare result sets (order-insensitive, float
rounded to 2dp). A parse error, a rejected statement, a timeout, or an
API call error all count as wrong — never silently dropped.

Writes:
    results/per_item.csv     (overwritten in place, with scoring columns added)
    results/summary.csv      (n_correct / 50, broken down by model and difficulty)

Prints 3 wrong answers per model, as the brief requires.

Usage:
    python -m src.score
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DB_PATH, RESULTS_DIR  # noqa: E402
from src.db_utils import execute_readonly, rows_match  # noqa: E402

ROOT = Path(__file__).parent.parent
ITEMS_PATH = ROOT / "data" / "items.jsonl"
PER_ITEM_PATH = ROOT / RESULTS_DIR / "per_item.csv"
SUMMARY_PATH = ROOT / RESULTS_DIR / "summary.csv"
DB_FULL_PATH = ROOT / DB_PATH


def load_gold() -> dict[int, str]:
    gold = {}
    with ITEMS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                gold[rec["id"]] = rec["gold_sql"]
    return gold


def score_row(row: dict, gold_sql: str) -> dict:
    if row.get("call_error"):
        row["exec_ok"] = False
        row["exec_error"] = f"call_error: {row['call_error']}"
        row["correct"] = False
        return row

    gold_result = execute_readonly(str(DB_FULL_PATH), gold_sql)
    if not gold_result.ok:
        # Should never happen — make_items.py verifies every gold query.
        raise RuntimeError(f"gold SQL failed to execute (item {row['item_id']}): {gold_result.error}")

    pred_result = execute_readonly(str(DB_FULL_PATH), row["raw_output"])
    if not pred_result.ok:
        row["exec_ok"] = False
        row["exec_error"] = pred_result.error
        row["correct"] = False
        return row

    row["exec_ok"] = True
    row["exec_error"] = ""
    row["correct"] = rows_match(gold_result.rows, pred_result.rows)
    return row


def main() -> None:
    gold = load_gold()

    with PER_ITEM_PATH.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        score_row(row, gold[int(row["item_id"])])

    fieldnames = list(rows[0].keys())
    with PER_ITEM_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # ---- summary ----
    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_model[row["model_key"]].append(row)

    summary_rows = []
    for model_key, model_rows in by_model.items():
        n = len(model_rows)
        n_correct = sum(1 for r in model_rows if r["correct"] in ("True", True))
        n_call_error = sum(1 for r in model_rows if r["call_error"])
        n_exec_error = sum(1 for r in model_rows if r["exec_ok"] in ("False", False) and not r["call_error"])
        by_diff = defaultdict(lambda: [0, 0])  # difficulty -> [correct, total]
        for r in model_rows:
            d = r["difficulty"]
            by_diff[d][1] += 1
            if r["correct"] in ("True", True):
                by_diff[d][0] += 1
        summary_rows.append({
            "model_key": model_key,
            "model_id": model_rows[0]["model_id"],
            "role": model_rows[0]["role"],
            "n_total": n,
            "n_correct": n_correct,
            "accuracy": round(n_correct / n, 4) if n else None,
            "n_call_errors": n_call_error,
            "n_sql_exec_errors": n_exec_error,
            "easy_acc": f"{by_diff['easy'][0]}/{by_diff['easy'][1]}",
            "medium_acc": f"{by_diff['medium'][0]}/{by_diff['medium'][1]}",
            "hard_acc": f"{by_diff['hard'][0]}/{by_diff['hard'][1]}",
        })

    with SUMMARY_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Wrote {SUMMARY_PATH}\n")
    for s in summary_rows:
        print(f"{s['model_key']:10s} {s['n_correct']:2d}/{s['n_total']}  "
              f"(easy {s['easy_acc']}, medium {s['medium_acc']}, hard {s['hard_acc']})  "
              f"call_errors={s['n_call_errors']} sql_errors={s['n_sql_exec_errors']}")

    print("\n--- 3 wrong answers per model ---")
    for model_key, model_rows in by_model.items():
        wrong = [r for r in model_rows if r["correct"] not in ("True", True)][:3]
        print(f"\n{model_key}:")
        for r in wrong:
            reason = r["exec_error"] or "result mismatch"
            print(f"  item {r['item_id']} [{r['difficulty']}]: {r['question'][:80]}")
            print(f"    generated: {r['raw_output'][:150]!r}")
            print(f"    reason: {reason[:150]}")


if __name__ == "__main__":
    main()
