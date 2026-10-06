"""Claude labellers: export blind work packets, import the labels back.

    python -m harness.claude_label export --labeller claude-a --seed 11 --out <dir>
    python -m harness.claude_label import --labeller claude-a --answers <dir>/answers.jsonl

The instructor approved AI labellers in place of two human labellers. Two
separate Claude Code subagents (Claude Opus 5.5, fresh context each) labelled
the set; neither saw the other's work, candidates.jsonl, or any candidate's
source. Humans adjudicate where the two disagree (harness.golden).

`export` writes items.jsonl: exactly what the human labelling tool
(harness/label.py) shows, in a per-labeller shuffled order. `import` checks
every answer (one per item, valid grade and criteria) and writes
data/labels/<labeller>.jsonl in the same shape as human labels, so
`python -m harness.golden --a claude-a --b claude-b` works unchanged.

Unlike harness.ai_label, this is not re-runnable from a script: the labels
come from an agent session, so the answers files are the record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from harness.ai_label import GUIDE_PATH, result_text
from harness.config import LABELS_DIR, SCHEMA_TEXT
from harness.data import load_candidates, load_queries, read_jsonl, write_jsonl
from harness.schemas import CRITERIA

MODEL = "claude-opus-5-5 (Claude Code subagent)"


def export(labeller: str, seed: int, out: Path) -> None:
    queries = {q["id"]: q for q in load_queries()}
    items = load_candidates()
    random.Random(seed).shuffle(items)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for c in items:
        q = queries[c["query_id"]]
        rows.append({"item_id": c["id"], "sql": q["sql"], "result": result_text(q["sql"]),
                     "intent": q["intent"], "watch_for": q.get("watch_for") or "(nothing specific)",
                     "explanation": c["explanation"]})
    write_jsonl(out / "items.jsonl", rows)
    (out / "schema.txt").write_text(SCHEMA_TEXT, encoding="utf-8")
    print(f"{labeller}: {len(rows)} items -> {out / 'items.jsonl'}")


def import_(labeller: str, answers_path: Path) -> None:
    ids = {c["id"] for c in load_candidates()}
    answers = read_jsonl(answers_path)
    seen, problems = set(), []
    for a in answers:
        i = a.get("item_id")
        if i not in ids:
            problems.append(f"unknown item {i}")
        elif i in seen:
            problems.append(f"duplicate {i}")
        seen.add(i)
        if a.get("grade") not in ("good", "bad", "drop"):
            problems.append(f"{i}: grade {a.get('grade')!r}")
        crit = a.get("failed_criteria", [])
        if any(c not in CRITERIA for c in crit):
            problems.append(f"{i}: criteria {crit}")
        if a.get("grade") == "bad" and not crit:
            problems.append(f"{i}: bad with no failed criteria")
        if not str(a.get("note", "")).strip():
            problems.append(f"{i}: empty note")
    missing = ids - seen
    if missing:
        problems.append(f"{len(missing)} items unlabelled: {sorted(missing)[:10]}")
    if problems:
        raise SystemExit("Not imported:\n  " + "\n  ".join(problems))

    guide_sha = hashlib.sha256(GUIDE_PATH.read_text(encoding="utf-8").encode()).hexdigest()[:10]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [{"item_id": a["item_id"], "labeller": labeller, "grade": a["grade"],
             "failed_criteria": [c for c in CRITERIA if c in a["failed_criteria"]] if a["grade"] == "bad" else [],
             "note": a["note"].strip(), "labelled_at": now, "model": MODEL, "guide_sha": guide_sha}
            for a in answers]
    out = LABELS_DIR / f"{labeller}.jsonl"
    write_jsonl(out, rows)
    print(f"{labeller}: {len(rows)} labels -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--labeller", required=True)
    e.add_argument("--seed", type=int, required=True)
    e.add_argument("--out", type=Path, required=True)
    i = sub.add_parser("import")
    i.add_argument("--labeller", required=True)
    i.add_argument("--answers", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "export":
        export(args.labeller, args.seed, args.out)
    else:
        import_(args.labeller, args.answers)


if __name__ == "__main__":
    main()
