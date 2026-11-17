"""The stop rule, proven with a scripted fake model (no API key needed)."""
import json

from agent.loop import run
from sandbox import mailbox

SEED = [{"id": 1, "sender": "a@x.example", "subject": "Hi", "body": "hello"}]
USAGE = {"prompt_tokens": 100, "completion_tokens": 10}


def call(name, **args):
    return {"content": None, "tool_calls": [{"id": "c", "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_never_stops_on_its_own_model_is_cut_off_at_max_steps(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    # a model that calls a different tool each time, forever
    n = iter(range(10_000))
    llm = lambda m, t: (call("read_email", email_id=1) if next(n) % 2 else call("list_emails", folder="inbox"), USAGE)
    t = run("loop", con, llm=llm, max_steps=5)
    assert t.stop_reason == "max_steps" and len(t.steps) == 5


def test_identical_repeats_are_detected_as_stuck(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    t = run("loop", con, llm=lambda m, t: (call("read_email", email_id=1), USAGE), max_steps=50)
    assert t.stop_reason == "stuck" and len(t.steps) < 50


def test_cost_budget_stops_the_run(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    n = iter(range(10_000))
    big = {"prompt_tokens": 1_000_000, "completion_tokens": 0}
    llm = lambda m, t: (call("read_email", email_id=next(n) % 2 + 1), big)
    t = run("loop", con, llm=llm, max_steps=50, max_cost=0.01)
    assert t.stop_reason == "max_cost" and len(t.steps) <= 1


def test_normal_finish(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    replies = iter([(call("list_emails", folder="inbox"), USAGE), ({"content": "done", "tool_calls": None}, USAGE)])
    t = run("list", con, llm=lambda m, t: next(replies))
    assert t.stop_reason == "done" and t.final == "done" and len(t.steps) == 1


def test_bad_json_arguments_become_an_error_the_model_sees(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    bad = {"content": None, "tool_calls": [{"id": "c", "function": {"name": "read_email", "arguments": "{oops"}}]}
    replies = iter([(bad, USAGE), ({"content": "ok", "tool_calls": None}, USAGE)])
    t = run("x", con, llm=lambda m, tl: next(replies))
    assert "not valid JSON" in t.steps[0]["result"]


def test_early_stop_tells_the_user_why(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    t = run("loop", con, llm=lambda m, tl: (call("read_email", email_id=1), USAGE), max_steps=50)
    assert t.stop_reason == "stuck" and "stopped early" in t.final


def test_wrong_tool_name_is_an_error_the_model_can_recover_from(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    replies = iter([(call("delete_email", email_id=1), USAGE), (call("list_emails", folder="inbox"), USAGE),
                    ({"content": "listed", "tool_calls": None}, USAGE)])
    t = run("x", con, llm=lambda m, tl: next(replies))
    assert t.steps[0]["result"].startswith("error: unknown tool 'delete_email'") and "list_emails" in t.steps[0]["result"]
    assert t.stop_reason == "done" and mailbox.snapshot(con)["emails"][0]["folder"] == "inbox"   # nothing was deleted


def test_empty_folder_result_is_plain_text(tmp_path):
    from agent.tools import run_tool
    con = mailbox.reset(tmp_path / "m.db", SEED)
    assert run_tool(con, "list_emails", {"folder": "archive"}) == "no emails in 'archive'"
