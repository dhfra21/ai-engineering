"""Model labellers -> data/labels/ai-<model>.jsonl

    python -m harness.ai_label                      # both labellers, all items
    python -m harness.ai_label --model qwen27b      # one labeller
    python -m harness.ai_label --limit 5            # smoke test

The instructor approved model labellers in place of two human labellers.
Each model labels every candidate on its own, from the full labelling guide,
and sees what the human labelling tool (harness/label.py) shows: the SQL, the
real result rows and the reference notes. Never the candidate's source.

Rows have the same shape as human labels, plus provenance (model, prompt,
guide sha), so `python -m harness.golden --a ai-qwen27b --b ai-gptoss20bhigh`
works unchanged. Humans then adjudicate the disagreements.

Neither labeller may be the judge model: the judge is evaluated against these
labels, and a model agreeing with itself proves nothing.

Labels are appended one at a time, so a run stopped by the daily cap resumes
where it left off. A failed call writes nothing and is retried on the next run.
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone

from harness import prompts
from harness.config import JUDGE_MODEL, LABELLER_MODELS, LABELS_DIR, MAX_TOKENS, MODELS, ROOT, SCHEMA_TEXT
from harness.data import append_jsonl, load_candidates, load_queries, preview_result, read_jsonl
from harness.llm import DailyLimitReached, call_json

PROMPT_VERSION = "v1"
GUIDE_PATH = ROOT / "data" / "LABELLING_GUIDE.md"


def result_text(sql: str) -> str:
    """The same preview a human labeller sees, flattened to text."""
    try:
        cols, rows, n = preview_result(sql)
    except Exception as e:  # noqa: BLE001 — a preview failure should not stop labelling
        return f"(result preview failed: {e})"
    lines = [f"{n} row(s). First {len(rows)}:", "  " + " | ".join(cols)]
    lines += ["  " + " | ".join(str(v) for v in r) for r in rows]
    return "\n".join(lines)


def label_all(model_key: str, limit: int | None) -> int:
    """Label every candidate not yet labelled by this model. Returns the number of failures."""
    if MODELS[model_key].model_id == MODELS[JUDGE_MODEL].model_id:
        raise SystemExit(f"{model_key} is the judge model; it cannot also make the golden labels.")
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    guide_sha = hashlib.sha256(guide.encode()).hexdigest()[:10]
    prompt = prompts.load("labeller", PROMPT_VERSION)
    name = f"ai-{model_key}"
    out_path = LABELS_DIR / f"{name}.jsonl"

    queries = {q["id"]: q for q in load_queries()}
    items = load_candidates()[:limit] if limit else load_candidates()
    done = {r["item_id"] for r in read_jsonl(out_path)}
    todo = [c for c in items if c["id"] not in done]
    print(f"{name}: {len(done)} already labelled, {len(todo)} to go")

    failures = []
    for i, item in enumerate(todo, start=1):
        q = queries[item["query_id"]]
        messages = prompt.render(guide=guide, schema=SCHEMA_TEXT, sql=q["sql"], result=result_text(q["sql"]),
                                 intent=q["intent"], watch_for=q.get("watch_for") or "(nothing specific)",
                                 explanation=item["explanation"])
        res = call_json(model_key, messages, "label", MAX_TOKENS["label"])
        if not res.ok:
            failures.append((item["id"], res.error))
            print(f"  [{i}/{len(todo)}] {item['id']} FAILED: {res.error[:120]}")
            continue
        grade = res.data["grade"]
        append_jsonl(out_path, {
            "item_id": item["id"],
            "labeller": name,
            "grade": grade,
            "failed_criteria": res.data["failed_criteria"] if grade == "bad" else [],
            "note": res.data["reason"],
            "labelled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": MODELS[model_key].model_id,
            "model_settings": MODELS[model_key].extra,
            "prompt": prompt.tag,
            "prompt_sha": prompt.sha,
            "guide_sha": guide_sha,
        })
        print(f"  [{i}/{len(todo)}] {item['id']} {grade}")

    total = len(read_jsonl(out_path))
    print(f"{name}: {total}/{len(items)} labelled in {out_path}")
    if failures:
        print(f"  {len(failures)} failed (rerun to retry; record persistent ones in the postmortem):")
        for item_id, err in failures:
            print(f"    {item_id} {err[:120]}")
    return len(failures)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=LABELLER_MODELS, help="only this labeller (default: both)")
    ap.add_argument("--limit", type=int, help="only the first N candidates (smoke test)")
    args = ap.parse_args()

    try:
        for key in [args.model] if args.model else LABELLER_MODELS:
            label_all(key, args.limit)
    except DailyLimitReached as e:
        print(f"\nStopped: {e}\nLabels so far are saved; rerun later to continue.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
