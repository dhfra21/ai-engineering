"""How a refusal threshold on the best reranker score trades wrong refusals against missed ones.

  python -m eval.threshold_check            # scores the paraphrased set (retrieval only, no LLM calls),
                                            # reuses the main-set scores stored in results/generation_tuned_judgefix.json

For each threshold t: the share of answerable questions that would be refused (score < t, bad) and the share of
unanswerable questions that would be refused (good). The threshold is tuned on the main set, so the paraphrased
set is the honest check. Writes results/threshold_check.md and .json.
"""
import json
from pathlib import Path

from eval.gold import load_qa
from src.retrieve import get_retriever

RESULTS = Path(__file__).resolve().parents[1] / "results"
THRESHOLDS = (0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0)


def top_scores_hard(strategy="article-oai"):
    r = get_retriever(strategy)
    r.search("warm-up", mode="hybrid+rerank", k=1)
    return {it["id"]: r.search(it["question"], mode="hybrid+rerank", k=5)[0]["score"] for it in load_qa(True, "qa_hard")}


def table(scores_by_group):
    lines = ["| threshold | " + " | ".join(f"{g} refused" for g in scores_by_group) + " |", "|---|" + "---|" * len(scores_by_group)]
    for t in THRESHOLDS:
        cells = [f"{100 * sum(s < t for s in v) / len(v):.0f}% ({sum(s < t for s in v)}/{len(v)})" for v in scores_by_group.values()]
        lines.append(f"| {t:g} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    main_rows = json.loads((RESULTS / "generation_tuned_judgefix.json").read_text())["rows"]
    groups = {
        "answerable, main set (bad)": [r["top_score"] for r in main_rows if r["answerable"]],
        "answerable, paraphrased (bad)": list(top_scores_hard().values()),
        "unanswerable (good)": [r["top_score"] for r in main_rows if not r["answerable"]],
    }
    text = ("# Refusal threshold check\n\nShare of questions refused when the best reranker score is below the threshold.\n"
            "Wrong refusals (answerable) should be low, right refusals (unanswerable) high.\n\n" + table(groups) + "\n")
    (RESULTS / "threshold_check.md").write_text(text)
    (RESULTS / "threshold_check.json").write_text(json.dumps(groups, indent=1))
    print(text)


if __name__ == "__main__":
    main()
