"""Wiring tests with a fake pipeline output: no network, no models."""
from eval.generation_eval import score_row, summarise

ITEM = {"id": "q1-fr", "lang": "fr", "answerable": True, "question": "Q ?", "answer": "A",
        "gold_doc": "law-1-1", "gold_articles": [2], "evidence": "x" * 10}
GOLD = {"id": "law-1-1:fr:0", "doc_id": "law-1-1", "article": "Art. 2", "text": "t"}
OTHER = {"id": "law-9-9:fr:0", "doc_id": "law-9-9", "article": "Art. 2", "text": "t"}
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


def test_faithfulness_judge_sees_the_numbers_the_answer_cites(monkeypatch):
    """A regression: sources were renumbered 1..k, so an answer citing [3][4] was judged against [1][2]."""
    from eval import judge
    seen = []
    monkeypatch.setattr(judge, "_call", lambda prompt, model: seen.append(prompt) or {"text": '{"faithful": true}', "usage": {"cost_usd": 0}})
    judge.judge_faithful("Réponse [3][4]", [{"text": "texte trois"}, {"text": "texte quatre"}], numbers=[3, 4])
    assert "[3] texte trois" in seen[0] and "[4] texte quatre" in seen[0] and "[1]" not in seen[0]
    judge.judge_faithful("Réponse", [{"text": "a"}, {"text": "b"}])          # no numbers: 1..k
    assert "[1] a" in seen[1] and "[2] b" in seen[1]


def test_score_row_passes_original_citation_numbers_to_the_judge(monkeypatch):
    from eval import generation_eval, judge
    calls = {}
    monkeypatch.setattr(judge, "judge_correct", lambda q, ref, ans: (True, "", 0.0))
    monkeypatch.setattr(judge, "judge_faithful", lambda ans, cited, numbers=None: calls.update(numbers=numbers) or (True, [], 0.0))
    o = out([GOLD], [OTHER, GOLD])
    o["cited"] = [2]
    row = score_row(ITEM, o)
    assert calls["numbers"] == [2] and row["faithful"] is True


def test_refusal_is_always_in_the_questions_language(monkeypatch):
    from src import generate

    class R:
        def search(self, q, **kw):
            return [{"id": "x", "text": "t", "score": 9.0}]

    monkeypatch.setattr(generate, "chat", lambda *a, **k: ("Je ne sais pas.", {"cost_usd": 0}))
    ar = generate.answer("ما هو الأجر الأدنى؟", retriever=R())
    fr = generate.answer("Quel est le prix ?", retriever=R())
    assert ar["abstained"] and ar["answer"] == "لا أعرف"          # the model said it in French; the question is Arabic
    assert fr["abstained"] and fr["answer"] == "Je ne sais pas"
    monkeypatch.setattr(generate, "chat", lambda *a, **k: ("Le délai est d'un mois [1]. Je ne sais pas le reste.", {"cost_usd": 0}))
    long = generate.answer("Quel délai ?", retriever=R())
    assert not long["abstained"] and "[1]" in long["answer"]       # a real answer is never replaced
