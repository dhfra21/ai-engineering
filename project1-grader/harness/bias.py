"""Two bias checks on the judge.

POSITION — does the order of two answers change the verdict?
    python -m harness.bias position --split dev
For each golden item, the pairwise judge compares the labelled explanation
with its alternative twice: (A=item, B=alt) and (A=alt, B=item). A reliable
judge picks the same underlying explanation both times. We report how often
the verdict flips, how often the first slot wins, and — on perturbed items,
where the alternative is the unbroken original — how often the judge picks
the answer we know is better.

VERBOSITY — does a longer answer get a better grade without being better?
    python -m harness.bias verbosity --split dev --pad template
    python -m harness.bias verbosity --split dev --pad llm
Each golden explanation is padded without adding information:
  template  fixed friendly preamble + generic SQL facts, no model call. The
            content is provably unchanged — the cleanest test.
  llm       a model rewrites it ~2x longer under instructions not to add or fix
            anything (prompts/pad/v1.md). More realistic filler, but the model
            might accidentally fix an error: spot-check the padded texts in
            the output file before trusting the number.
Then (1) the pointwise judge grades original and padded, and we count grade
changes, in particular bad -> good on answers humans labelled bad; and (2) the
pairwise judge compares original vs padded in both orders — a fair judge says
tie or prefers the original, never the padding.

Writes results/bias/<judge>_<split>/{position,verbosity-<pad>}.{jsonl,json}.
"""
from __future__ import annotations

import argparse
import json

from harness import judge, prompts, stats
from harness.config import JUDGE_MODEL, MAX_TOKENS, PAD_MODEL, is_mock, results_root
from harness.data import load_golden, write_jsonl
from harness.llm import DailyLimitReached, call_json

TEMPLATE_PREFIX = ("Great question! Here is a clear, step-by-step explanation of what this SQL "
                   "query does, written so that anyone can follow it.\n\n")
TEMPLATE_SUFFIX = ("\n\nAs background: a SELECT query like this one only reads data and never "
                   "changes anything in the database, so it is safe to run at any time. The "
                   "database works out the answer from the tables named in the query and shows "
                   "the result as a table of rows and columns. In short, the query gives you "
                   "exactly the information described above.")


def _map(winner: str | None, a_is: str, b_is: str) -> str | None:
    return {"A": a_is, "B": b_is, "tie": "tie"}.get(winner) if winner else None


def position(golden: list[dict], version: str, use_cache: bool) -> tuple[list[dict], dict]:
    rows = []
    for i, g in enumerate(golden, start=1):
        r1 = judge.compare(g, g["explanation"], g["alt_explanation"], version, use_cache=use_cache)
        r2 = judge.compare(g, g["alt_explanation"], g["explanation"], version, use_cache=use_cache)
        w1 = r1.data["winner"] if r1.ok else None
        w2 = r2.data["winner"] if r2.ok else None
        v1, v2 = _map(w1, "item", "alt"), _map(w2, "alt", "item")
        rows.append({
            "item_id": g["id"], "source": g["source"], "alt_source": g["alt_source"],
            "human_label_item": g["label"],
            "order1_winner_slot": w1, "order2_winner_slot": w2,
            "order1_prefers": v1, "order2_prefers": v2,
            "consistent": (v1 == v2) if None not in (v1, v2) else None,
            "reasons": [r1.data["reason"] if r1.ok else r1.error, r2.data["reason"] if r2.ok else r2.error],
            "cost_usd": r1.cost_usd + r2.cost_usd,
        })
        print(f"  [{i:3d}/{len(golden)}] {g['id']} order1={w1} order2={w2} "
              f"{'consistent' if rows[-1]['consistent'] else 'FLIP' if rows[-1]['consistent'] is False else 'error'}")

    ok = [r for r in rows if r["consistent"] is not None]
    slots = [r["order1_winner_slot"] for r in ok] + [r["order2_winner_slot"] for r in ok]
    # Known-better pairs: the item had one planted mistake, the alternative is the original.
    known = [r for r in ok if r["source"] == "perturbed" and r["human_label_item"] == "bad"]
    summary = {
        "pairs": len(rows), "errors": len(rows) - len(ok),
        "consistent": stats.proportion(sum(r["consistent"] for r in ok), len(ok)),
        "flipped": stats.proportion(sum(not r["consistent"] for r in ok), len(ok)),
        # A flip where each order picked whatever sat in slot A (or in slot B): pure position effect.
        "flipped_to_same_slot": stats.proportion(
            sum(r["order1_winner_slot"] == r["order2_winner_slot"] != "tie" for r in ok), len(ok)),
        "slot_wins_over_all_verdicts": {
            "A_first": stats.proportion(slots.count("A"), len(slots)),
            "B_second": stats.proportion(slots.count("B"), len(slots)),
            "tie": stats.proportion(slots.count("tie"), len(slots)),
        },
        "known_better_pairs": {
            "n": len(known),
            "picked_original_both_orders": stats.proportion(
                sum(r["order1_prefers"] == r["order2_prefers"] == "alt" for r in known), len(known)),
            "picked_broken_in_either_order": stats.proportion(
                sum("item" in (r["order1_prefers"], r["order2_prefers"]) for r in known), len(known)),
        },
        "cost_usd_total": round(sum(r["cost_usd"] for r in rows), 6),
    }
    return rows, summary


def pad(g: dict, mode: str, use_cache: bool) -> str | None:
    if mode == "template":
        return TEMPLATE_PREFIX + g["explanation"] + TEMPLATE_SUFFIX
    messages = prompts.load("pad", "v1").render(sql=g["sql"], explanation=g["explanation"])
    res = call_json(PAD_MODEL, messages, "pad", MAX_TOKENS["pad"], use_cache=use_cache)
    return res.data["explanation"] if res.ok else None


def verbosity(golden: list[dict], version: str, mode: str, use_cache: bool) -> tuple[list[dict], dict]:
    rows = []
    for i, g in enumerate(golden, start=1):
        padded = pad(g, mode, use_cache)
        if padded is None:
            rows.append({"item_id": g["id"], "error": "padding failed"})
            continue
        before = judge.grade(g, g["explanation"], version, use_cache=use_cache)
        after = judge.grade(g, padded, version, use_cache=use_cache)
        p1 = judge.compare(g, g["explanation"], padded, version, use_cache=use_cache)
        p2 = judge.compare(g, padded, g["explanation"], version, use_cache=use_cache)
        pw1 = _map(p1.data["winner"], "original", "padded") if p1.ok else None
        pw2 = _map(p2.data["winner"], "padded", "original") if p2.ok else None
        rows.append({
            "item_id": g["id"], "source": g["source"], "human": g["label"],
            "words_original": len(g["explanation"].split()), "words_padded": len(padded.split()),
            "judge_before": before.data["grade"] if before.ok else None,
            "judge_after": after.data["grade"] if after.ok else None,
            "reason_after": after.data["reason"] if after.ok else after.error,
            "pairwise_prefers": [pw1, pw2],
            "padded_explanation": padded,
            "error": None if (before.ok and after.ok) else (before.error or after.error),
        })
        print(f"  [{i:3d}/{len(golden)}] {g['id']} human={g['label']:4s} "
              f"judge {rows[-1]['judge_before']} -> {rows[-1]['judge_after']}  pairwise={pw1},{pw2}")

    ok = [r for r in rows if r.get("error") is None]

    def moved(frm: str, to: str, subset: list[dict]) -> dict:
        base = [r for r in subset if r["judge_before"] == frm]
        return stats.proportion(sum(r["judge_after"] == to for r in base), len(base))

    human_bad = [r for r in ok if r["human"] == "bad"]
    human_good = [r for r in ok if r["human"] == "good"]
    pw = [v for r in ok for v in r["pairwise_prefers"] if v is not None]
    words_o = sum(r["words_original"] for r in ok)
    summary = {
        "pad_mode": mode, "items": len(rows), "errors": len(rows) - len(ok),
        "length_ratio_words": round(sum(r["words_padded"] for r in ok) / words_o, 2) if words_o else None,
        "grade_changed": stats.proportion(sum(r["judge_before"] != r["judge_after"] for r in ok), len(ok)),
        "judge_bad_became_good": moved("bad", "good", ok),
        "judge_good_became_bad": moved("good", "bad", ok),
        # The failure that matters: a human-bad answer the judge caught, rescued by padding.
        "human_bad_rescued_by_padding": moved("bad", "good", human_bad),
        "human_good_penalised_by_padding": moved("good", "bad", human_good),
        "pairwise_verdicts": {
            "padded": stats.proportion(pw.count("padded"), len(pw)),
            "original": stats.proportion(pw.count("original"), len(pw)),
            "tie": stats.proportion(pw.count("tie"), len(pw)),
        },
    }
    return rows, summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("check", choices=["position", "verbosity"])
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--judge", default="v1", help="version used for both prompts/judge and prompts/judge_pairwise")
    ap.add_argument("--pad", choices=["template", "llm"], default="template")
    ap.add_argument("--limit", type=int, help="only the first N golden items")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    golden = load_golden(args.split)[:args.limit] if args.limit else load_golden(args.split)
    print(f"{args.check} bias, judge {args.judge} ({JUDGE_MODEL}), {len(golden)} {args.split} items"
          f"{' [MOCK BACKEND]' if is_mock() else ''}")
    try:
        if args.check == "position":
            rows, summary = position(golden, args.judge, not args.no_cache)
            name = "position"
        else:
            rows, summary = verbosity(golden, args.judge, args.pad, not args.no_cache)
            name = f"verbosity-{args.pad}"
    except DailyLimitReached as e:
        raise SystemExit(f"\nStopped: {e}")

    summary.update({"judge": args.judge, "judge_model": JUDGE_MODEL, "split": args.split, "limit": args.limit})
    out_dir = results_root() / "bias" / f"{args.judge}_{args.split}"
    write_jsonl(out_dir / f"{name}.jsonl", rows)
    (out_dir / f"{name}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    print(f"-> {out_dir}")


if __name__ == "__main__":
    main()
