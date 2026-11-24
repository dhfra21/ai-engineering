"""Structural injection guard: an id-scoped request cannot be widened by text in an email."""
import json

from agent.loop import named_ids, run
from sandbox import mailbox

SEED = [{"id": i, "sender": f"s{i}@x.example", "subject": "S", "body": "hi"} for i in (1, 2, 3, 14)]
USAGE = {"prompt_tokens": 10, "completion_tokens": 1}


def call(name, **a):
    return {"content": None, "tool_calls": [{"id": "c", "function": {"name": name, "arguments": json.dumps(a)}}]}


def test_named_ids():
    assert named_ids("Read email 14, then label it") == {14}
    assert named_ids("reply to DF (email 3) and read email 16") == {3, 16}
    assert named_ids("labels emails 1, 3 and 4") == {1, 3, 4}
    assert named_ids("label the billing mail") == set()


def test_write_outside_named_email_is_refused_even_if_model_obeys_injection(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    script = iter([call("label_email", email_id=1, label="spam", folder="archive"), call("label_email", email_id=14, label="newsletter"), {"content": "done", "tool_calls": None}])
    t = run("Read email 14, then label it as newsletter.", con, llm=lambda m, t: (next(script), USAGE))
    assert t.steps[0]["result"].startswith("error: refused")
    assert con.execute("SELECT labels FROM emails WHERE id=1").fetchone()[0] in ("", None)
    assert "newsletter" in con.execute("SELECT labels FROM emails WHERE id=14").fetchone()[0]


def test_unscoped_request_is_not_restricted(tmp_path):
    con = mailbox.reset(tmp_path / "m.db", SEED)
    script = iter([call("label_email", email_id=2, label="newsletter"), {"content": "done", "tool_calls": None}])
    t = run("label the newsletters", con, llm=lambda m, t: (next(script), USAGE))
    assert t.steps[0]["result"].startswith("ok")
