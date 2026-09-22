"""Interactive labelling tool. Each labeller runs it on their own:

    python -m harness.label --labeller alice
    python -m harness.label --labeller bob

Labels are appended to data/labels/<labeller>.jsonl one at a time, so you can
quit (q) and resume whenever. Items come in the same shuffled order for
everyone. You never see where a candidate came from, nor the other
labeller's file — do not open it until you are both done (LABELLING_GUIDE.md §4).

Keys:  g = good   b = bad   d = propose dropping the item   s = show schema
       u = undo your last label   q = quit
"""
from __future__ import annotations

import argparse
import random
import re
import textwrap
from datetime import datetime, timezone

from harness.config import LABELS_DIR, SCHEMA_TEXT
from harness.data import append_jsonl, load_candidates, load_queries, preview_result, read_jsonl, write_jsonl
from harness.schemas import CRITERIA

ORDER_SEED = 7
CRITERIA_HELP = {
    "correct": "a statement about what the query does is wrong",
    "complete": "a filter / grouping / aggregate / DISTINCT / LIMIT / ORDER BY is missing",
    "no_invention": "claims something the query does not support",
    "clear": "a non-SQL reader could not follow it",
}
_KEYWORDS = r"\b(FROM|WHERE|GROUP BY|HAVING|ORDER BY|LIMIT|UNION ALL|UNION|INTERSECT|EXCEPT|LEFT JOIN|JOIN|WITH|SELECT)\b"


def pretty_sql(sql: str) -> str:
    out = re.sub(r"\s+" + _KEYWORDS, r"\n  \1", sql.strip())
    return out


def show(item: dict, query: dict, i: int, total: int) -> None:
    bar = "=" * 78
    print(f"\n{bar}\n[{i}/{total}]  {item['id']}   difficulty: {query['difficulty']}\n{bar}")
    print("SQL:\n  " + pretty_sql(query["sql"]))
    try:
        cols, rows, n = preview_result(query["sql"])
        print(f"\nResult: {n} row(s). First {len(rows)}:")
        print("  " + " | ".join(cols))
        for r in rows:
            print("  " + " | ".join(str(v) for v in r))
    except Exception as e:  # noqa: BLE001 — a preview failure should not stop labelling
        print(f"\n(result preview failed: {e})")
    print(f"\nAuthor's note (reference): {query['intent']}")
    if query.get("watch_for"):
        print(f"Known trap (reference):   {query['watch_for']}")
    print("\nEXPLANATION TO LABEL:")
    for para in item["explanation"].splitlines() or [""]:
        print(textwrap.fill(para, width=78, initial_indent="  ", subsequent_indent="  ") or "")
    print()


def ask_criteria() -> list[str]:
    print("Which criteria fail? (numbers, e.g. '1 3')")
    for n, c in enumerate(CRITERIA, start=1):
        print(f"  {n}. {c:13s} — {CRITERIA_HELP[c]}")
    while True:
        raw = input("> ").split()
        try:
            picked = sorted({CRITERIA[int(x) - 1] for x in raw}, key=CRITERIA.index)
        except (ValueError, IndexError):
            picked = []
        if picked:
            return picked
        print("Pick at least one number from 1-4.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labeller", required=True, help="your name, used as the file name")
    ap.add_argument("--split", default="all", choices=["all", "dev", "test"])
    args = ap.parse_args()

    name = re.sub(r"[^a-z0-9_-]", "", args.labeller.lower())
    out_path = LABELS_DIR / f"{name}.jsonl"
    queries = {q["id"]: q for q in load_queries()}
    items = [c for c in load_candidates() if args.split in ("all", c["split"])]
    random.Random(ORDER_SEED).shuffle(items)

    while True:
        done = {r["item_id"] for r in read_jsonl(out_path)}
        todo = [c for c in items if c["id"] not in done]
        if not todo:
            print(f"All {len(items)} items labelled in {out_path}. Thank you!")
            return
        item = todo[0]
        show(item, queries[item["query_id"]], len(done) + 1, len(items))

        choice = input("[g]ood  [b]ad  [d]rop  [s]chema  [u]ndo  [q]uit > ").strip().lower()
        if choice == "q":
            print(f"Saved. {len(done)}/{len(items)} done. Resume with the same command.")
            return
        if choice == "s":
            print("\n" + SCHEMA_TEXT)
            input("(enter to continue)")
            continue
        if choice == "u":
            rows = read_jsonl(out_path)
            if rows:
                write_jsonl(out_path, rows[:-1])
                print(f"Removed your label for {rows[-1]['item_id']}.")
            continue
        if choice not in ("g", "b", "d"):
            continue

        grade = {"g": "good", "b": "bad", "d": "drop"}[choice]
        failed = ask_criteria() if grade == "bad" else []
        prompt = "Why drop it? (required) > " if grade == "drop" else "Note (optional, enter to skip) > "
        note = input(prompt).strip()
        while grade == "drop" and not note:
            note = input(prompt).strip()

        append_jsonl(out_path, {
            "item_id": item["id"],
            "labeller": name,
            "grade": grade,
            "failed_criteria": failed,
            "note": note,
            "labelled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })


if __name__ == "__main__":
    main()
