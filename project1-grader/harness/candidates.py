"""Make the candidate explanations the humans will label -> data/candidates.jsonl

    python -m harness.candidates            # all 161 queries
    python -m harness.candidates --limit 5  # smoke test

A golden set where every answer is good cannot tell a judge apart from one
that always says "good". So each query gets ONE candidate to label, drawn
from a seeded mix of sources:

    baseline   the system (system/v1 on SYSTEM_MODEL)       ~45%
    weak       the same prompt on a small model (WEAK_MODEL) ~20%
    perturbed  a baseline answer with one planted mistake    ~35%
               (wrong_filter, missing_condition, wrong_aggregation,
                wrong_join_semantics, invented_detail, jargon)

The source is stored but hidden from labellers and the judge; it is only
used afterwards to break results down (e.g. "the judge misses 40% of
invented_detail errors"). Each candidate also carries an `alt_explanation`
from a different source, used only for pairwise position-bias tests.

This file is generated ONCE. Labels refer to candidate ids, so regenerating
would silently invalidate them — the script refuses to overwrite without
--force.
"""
from __future__ import annotations

import argparse
import random

from harness import prompts
from harness.config import CANDIDATES_PATH, MAX_TOKENS, PERTURB_MODEL, SYSTEM_MODEL, WEAK_MODEL
from harness.data import load_queries, write_jsonl
from harness.llm import DailyLimitReached, call_json
from harness.system import explain

SEED = 2026
SOURCE_WEIGHTS = {"baseline": 0.45, "weak": 0.20, "perturbed": 0.35}
ERROR_TYPES = ["wrong_filter", "missing_condition", "wrong_aggregation",
               "wrong_join_semantics", "invented_detail", "jargon"]
SYSTEM_PROMPT_VERSION = "v1"
PERTURB_PROMPT_VERSION = "v1"


def assign_sources(n: int) -> list[str]:
    """Exact proportions (not independent coin flips), shuffled with a fixed seed."""
    rng = random.Random(SEED)
    counts = {k: round(w * n) for k, w in SOURCE_WEIGHTS.items()}
    counts["baseline"] += n - sum(counts.values())
    sources = [s for s, c in counts.items() for _ in range(c)]
    rng.shuffle(sources)
    return sources


def assign_error_types(n: int) -> list[str]:
    rng = random.Random(SEED + 1)
    types = [ERROR_TYPES[i % len(ERROR_TYPES)] for i in range(n)]
    rng.shuffle(types)
    return types


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, help="only the first N queries (smoke test)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing candidates file")
    args = ap.parse_args()

    if CANDIDATES_PATH.exists() and not args.force:
        raise SystemExit(f"{CANDIDATES_PATH} already exists and labels may point at it. "
                         f"Use --force only if nobody has started labelling.")

    queries = load_queries()
    sources = assign_sources(len(queries))
    error_types = iter(assign_error_types(sources.count("perturbed")))
    if args.limit:
        queries, sources = queries[:args.limit], sources[:args.limit]

    perturb_prompt = prompts.load("perturb", PERTURB_PROMPT_VERSION)
    rows, failures = [], []
    try:
        for i, (q, source) in enumerate(zip(queries, sources), start=1):
            error_type = next(error_types) if source == "perturbed" else None
            print(f"[{i}/{len(queries)}] {q['id']} {source}{' / ' + error_type if error_type else ''}")

            baseline = explain(q["sql"], SYSTEM_PROMPT_VERSION, SYSTEM_MODEL)
            if not baseline.ok:
                failures.append((q["id"], "baseline", baseline.error))
                continue
            base_text = baseline.data["explanation"]

            weak_text = None
            if source in ("baseline", "weak"):
                weak = explain(q["sql"], SYSTEM_PROMPT_VERSION, WEAK_MODEL)
                if not weak.ok:
                    failures.append((q["id"], "weak", weak.error))
                    continue
                weak_text = weak.data["explanation"]

            perturbation = None
            if source == "baseline":
                text, alt_text, alt_source = base_text, weak_text, "weak"
            elif source == "weak":
                text, alt_text, alt_source = weak_text, base_text, "baseline"
            else:
                messages = perturb_prompt.render(sql=q["sql"], explanation=base_text, error_type=error_type)
                res = call_json(PERTURB_MODEL, messages, "perturb", MAX_TOKENS["perturb"])
                if not res.ok:
                    failures.append((q["id"], "perturb", res.error))
                    continue
                text, alt_text, alt_source = res.data["explanation"], base_text, "baseline"
                perturbation = {"error_type": error_type, "change_made": res.data["change_made"],
                                "model": PERTURB_MODEL, "prompt": perturb_prompt.tag}

            rows.append({
                "id": f"c-{q['id']}",
                "query_id": q["id"],
                "split": q["split"],
                "difficulty": q["difficulty"],
                "explanation": text,
                "source": source,
                "source_model": WEAK_MODEL if source == "weak" else SYSTEM_MODEL,
                "perturbation": perturbation,
                "alt_explanation": alt_text,
                "alt_source": alt_source,
                "system_prompt": f"system/{SYSTEM_PROMPT_VERSION}",
            })
    except DailyLimitReached as e:
        print(f"\nStopped: {e}")
        print("Nothing written. Calls so far are cached — rerun later and they are not repeated.")
        raise SystemExit(1)

    write_jsonl(CANDIDATES_PATH, rows)
    print(f"\nWrote {len(rows)} candidates to {CANDIDATES_PATH}")
    for s in SOURCE_WEIGHTS:
        print(f"  {s}: {sum(r['source'] == s for r in rows)}")
    if failures:
        print(f"  {len(failures)} queries skipped because a call failed "
              f"(record these in the postmortem):")
        for qid, stage, err in failures:
            print(f"    {qid} [{stage}] {err[:120]}")


if __name__ == "__main__":
    main()
