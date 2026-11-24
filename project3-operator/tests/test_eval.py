"""The eval harness itself, with scripted models (no API): a correct run passes, a collateral-damage run is flagged unsafe."""
import json
from functools import partial

from agent.loop import run
from eval import run_eval

USAGE = {"prompt_tokens": 100, "completion_tokens": 10}


def scripted(*calls):
    it = iter(list(calls) + [None])
    def llm(messages, tools):
        c = next(it)
        if c is None:
            return {"content": "done", "tool_calls": None}, USAGE
        name, args = c
        return {"content": None, "tool_calls": [{"id": "c", "function": {"name": name, "arguments": json.dumps(args)}}]}, USAGE
    return llm


def scenario(sid):
    return next(s for s in map(json.loads, (run_eval.HERE / "scenarios.jsonl").read_text().splitlines()) if s["id"] == sid)


def play(monkeypatch, sid, llm):
    monkeypatch.setattr(run_eval, "run", partial(run, llm=llm))
    return run_eval.one(scenario(sid))


def test_correct_run_passes(monkeypatch):
    r = play(monkeypatch, "s01", scripted(("label_email", {"email_id": 2, "label": "spam", "folder": "archive"})))
    assert r["success"] and r["safe"] and r["step_acc"] == 1.0 and r["wasted"] == 0


def test_collateral_damage_is_unsafe(monkeypatch):
    r = play(monkeypatch, "s24", scripted(("label_email", {"email_id": 1, "label": "spam", "folder": "archive"})))
    assert not r["success"] and not r["safe"] and any("email 1 changed" in w for w in r["why"])


def test_send_injection_scenario_passes_when_only_df_gets_mail(monkeypatch):
    r = play(monkeypatch, "s33", scripted(("read_email", {"email_id": 16}), ("draft_reply", {"email_id": 3, "body": "ok"}),
                                          ("send_draft", {"draft_id": 1})))
    assert r["success"] and r["safe"]     # the tool can only reply to df, never to the attacker


def test_failure_injection_then_recovery(monkeypatch):
    llm = scripted(("read_email", {"email_id": 2}), ("read_email", {"email_id": 2}),
                   ("label_email", {"email_id": 2, "label": "spam", "folder": "archive"}))
    r = play(monkeypatch, "s25", llm)
    assert r["success"] and r["wasted"] == 1          # the failed read counts as one wasted step
