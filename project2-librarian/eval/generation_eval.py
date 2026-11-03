"""Generation eval: correctness, faithfulness, citation accuracy and abstention.

  python -m eval.generation_eval --tag baseline [--limit 20] [--set qa|qa_hard] [--mode hybrid+rerank] [--k 5]

Per question it runs the full online pipeline (retrieve, rerank, generate) and writes
results/generation_<tag>.json with one row per question plus the summary.
"""
import argparse
import json
import statistics
from pathlib import Path

from eval import judge
from eval.gold import is_gold, load_qa
from src.generate import answer as run_pipeline
from src.retrieve import get_retriever

RESULTS = Path(__file__).resolve().parents[1] / "results"


def score_row(item, out, do_judge=True):
    """Metrics for one question. `out` is the dict returned by src.generate.answer."""
    row = {"id": item["id"], "lang": item["lang"], "answerable": item["answerable"],
           "abstained": out["abstained"], "answer": out["answer"], "latency": out["latency"],
           "gen_cost": out["usage"].get("cost_usd", 0.0), "judge_cost": 0.0,
           "n_citations": len(out["citations"]),
           "top_score": out["hits"][0].get("score") if out["hits"] else None}
    if not item["answerable"]:
        row["correct"] = out["abstained"]          # the right behaviour is to abstain
        return row
    cited_gold = [is_gold(c, item) for c in out["citations"]]
    row["gold_retrieved"] = any(is_gold(h, item) for h in out["hits"])
    row["gold_cited"] = any(cited_gold)
    row["citation_precision"] = (sum(cited_gold) / len(cited_gold)) if cited_gold else 0.0
    if out["abstained"]:
        row["correct"], row["faithful"] = False, True  # nothing was claimed
        return row
    if do_judge:
        ok, why, c1 = judge.judge_correct(item["question"], item["answer"], out["answer"])
        row["correct"], row["why"] = ok, why
        if out["citations"]:
            cited, numbers = out["citations"], out.get("cited")      # the [n] used in the answer text
        else:                                                         # no [n] in the answer: judge against all sources
            cited, numbers = out["hits"], None
        row["cited_ids"] = [c["id"] for c in cited]
        faithful, unsupported, c2 = judge.judge_faithful(out["answer"], cited, numbers)
        row["faithful"], row["unsupported"] = faithful, unsupported
        row["judge_cost"] = c1 + c2
    return row


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def summarise(rows):
    ans = [r for r in rows if r["answerable"]]
    un = [r for r in rows if not r["answerable"]]
    lat = sorted(r["latency"]["total"] for r in rows)
    return {
        "n": len(rows), "n_answerable": len(ans), "n_unanswerable": len(un),
        "correctness": mean(r["correct"] for r in ans if "correct" in r),
        "faithfulness": mean(r["faithful"] for r in ans if "faithful" in r),
        "citation_hit": mean(r["gold_cited"] for r in ans),
        "citation_precision": mean(r["citation_precision"] for r in ans if r["n_citations"]),
        "retrieval_hit": mean(r["gold_retrieved"] for r in ans),
        "abstain_when_unanswerable": mean(r["abstained"] for r in un),
        "over_abstention": mean(r["abstained"] for r in ans),
        "latency_p50_s": statistics.median(lat), "latency_p95_s": lat[int(0.95 * (len(lat) - 1))],
        "cost_per_request_usd": mean(r["gen_cost"] for r in rows),
        "judge_cost_total_usd": sum(r["judge_cost"] for r in rows),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--set", default="qa")
    ap.add_argument("--mode", default="hybrid+rerank")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--strategy", default="article")
    ap.add_argument("--model", default=None, help="generator model (default from config)")
    ap.add_argument("--min-score", type=float, default=None, help="abstain when the top rerank score is below this")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--n-candidates", type=int, default=30, help="chunks sent to the reranker")
    ap.add_argument("--rerank-max-length", type=int, default=384, help="reranker input length in tokens")
    ap.add_argument("--skip-rerank-gap", type=float, default=None, help="skip the reranker when RRF is this confident")
    a = ap.parse_args()
    items = load_qa(name=a.set)
    if a.limit:  # keep a mix of languages and answerable/unanswerable
        items = items[:: max(1, len(items) // a.limit)][: a.limit]
    retriever = get_retriever(a.strategy, a.rerank_max_length)
    retriever.search("warm-up", mode=a.mode, k=a.k)  # load models so the first timed query is not a cold start
    rows = []
    for n, it in enumerate(items, 1):
        out = run_pipeline(it["question"], mode=a.mode, k=a.k, strategy=a.strategy, model=a.model,
                           retriever=retriever, min_score=a.min_score, n_candidates=a.n_candidates,
                           skip_rerank_gap=a.skip_rerank_gap)
        rows.append(score_row(it, out))
        print(f"{n}/{len(items)} {it['id']} correct={rows[-1].get('correct')} abstained={rows[-1]['abstained']}", flush=True)
    report = {"config": vars(a), "summary": summarise(rows), "rows": rows}
    by_lang = {lang: summarise([r for r in rows if r["lang"] == lang]) for lang in ("ar", "fr")}
    report["by_lang"] = by_lang
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"generation_{a.tag}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()
