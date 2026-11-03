"""Wiring tests with a fake pipeline output: no network, no models."""
from eval.generation_eval import score_row, summarise

ITEM = {"id": "q1-fr", "lang": "fr", "answerable": True, "question": "Q ?", "answer": "A",
        "gold_doc": "law-1-1", "gold_articles": [2], "evidence": "x" * 10}
GOLD = {"doc_id": "law-1-1", "article": "Art. 2", "text": "t"}
OTHER = {"doc_id": "law-9-9", "article": "Art. 2", "text": "t"}
LAT = {"search": 0.1, "generate": 0.2, "total": 0.3}


def out(citations, hits, abstained=False, answer="réponse [1]"):
    return {"answer": answer, "abstained": abstained, "citations": citations, "hits": hits,
            "latency": LAT, "usage": {"cost_usd": 0.001}}


def test_abstaining_on_unanswerable_is_correct():
    item = {**ITEM, "answerable": False, "gold_doc": None, "gold_articles": []}
    assert score_row(item, out([], [], abstained=True, answer="Je ne sais pas"))["correct"] is True
    assert score_row(item, out([GOLD], [GOLD]), do_judge=False)["correct"] is False


def test_citation_metrics_without_judge():
    r = score_row(ITEM, out([GOLD, OTHER], [OTHER, GOLD]), do_judge=False)
    assert r["gold_retrieved"] and r["gold_cited"] and r["citation_precision"] == 0.5


def test_abstaining_on_answerable_counts_as_wrong_but_not_unfaithful():
    r = score_row(ITEM, out([], [GOLD], abstained=True, answer="Je ne sais pas"))
    assert r["correct"] is False and r["faithful"] is True and r["gold_retrieved"]


def test_summary_rates():
    rows = [score_row(ITEM, out([GOLD], [GOLD]), do_judge=False)]
    rows[0]["correct"], rows[0]["faithful"] = True, True
    un = score_row({**ITEM, "answerable": False, "gold_doc": None, "gold_articles": []},
                   out([], [], abstained=True, answer="Je ne sais pas"))
    s = summarise(rows + [un])
    assert s["correctness"] == 1.0 and s["abstain_when_unanswerable"] == 1.0 and s["cost_per_request_usd"] == 0.001
