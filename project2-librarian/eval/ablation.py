"""Collect the saved retrieval results into the ablation tables for the report.

  python -m eval.ablation            # prints markdown, writes results/ablation.md

Rows are search modes (keyword only, vector only, hybrid, hybrid + reranker); one table per
(question set, chunking strategy). Run eval.retrieval_eval for each combination first.
"""
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"
MODES = [("bm25", "keyword only (BM25)"), ("dense", "vector only"), ("hybrid", "hybrid (RRF)"),
         ("hybrid+rerank", "hybrid + reranker")]
SETS = {"qa": "main set (50 facts x 2 languages)", "qa_hard": "paraphrased set (25 facts x 2 languages)"}


def pct(x):
    return f"{100 * x:.0f}%"


def table(rep, title):
    lines = [f"### {title}", "",
             "| search | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | AR recall@5 | FR recall@5 | search p50 | search p95 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for mode, label in MODES:
        if mode not in rep:
            continue
        a, ar, fr = rep[mode]["all"], rep[mode]["ar"], rep[mode]["fr"]
        lat = lambda ms: f"{ms / 1000:.1f} s" if ms >= 1000 else f"{ms:.0f} ms"
        lines.append(f"| {label} | {pct(a['recall@1'])} | {pct(a['recall@3'])} | {pct(a['recall@5'])} | {pct(a['recall@10'])} "
                     f"| {a['mrr@10']:.3f} | {pct(ar['recall@5'])} | {pct(fr['recall@5'])} | {lat(a['search_p50_ms'])} | {lat(a['search_p95_ms'])} |")
    return "\n".join(lines)


def main():
    out = []
    for qset, desc in SETS.items():
        for strategy in ("article", "fixed"):
            f = RESULTS / f"retrieval_{qset}_{strategy}.json"
            if f.exists():
                out.append(table(json.loads(f.read_text()), f"{desc}, chunking = {strategy}"))
    text = "\n\n".join(out)
    (RESULTS / "ablation.md").write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
