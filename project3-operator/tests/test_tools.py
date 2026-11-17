import pytest

from agent.tools import run_tool
from sandbox import mailbox

SEED = [{"id": 1, "sender": "a@x.example", "subject": "Hi", "body": "hello"},
        {"id": 2, "sender": "b@x.example", "subject": "Promo", "body": "buy"}]


@pytest.fixture
def con(tmp_path):
    return mailbox.reset(tmp_path / "m.db", SEED)


def test_bad_arguments_give_clear_errors(con):
    assert run_tool(con, "nope", {}).startswith("error: unknown tool")
    assert "missing required" in run_tool(con, "read_email", {})
    assert "must be an integer" in run_tool(con, "read_email", {"email_id": "1"})
    assert "unexpected argument" in run_tool(con, "read_email", {"email_id": 1, "x": 2})
    assert "must be one of" in run_tool(con, "label_email", {"email_id": 1, "label": "urgent"})
    assert "no email with id 9" in run_tool(con, "read_email", {"email_id": 9})


def test_read_wraps_body_as_untrusted(con):
    assert "<untrusted_email>\nhello\n</untrusted_email>" in run_tool(con, "read_email", {"email_id": 1})


def test_label_is_idempotent(con):
    run_tool(con, "label_email", {"email_id": 2, "label": "spam", "folder": "archive"})
    before = mailbox.snapshot(con)
    run_tool(con, "label_email", {"email_id": 2, "label": "spam", "folder": "archive"})
    assert mailbox.snapshot(con) == before


def test_draft_is_idempotent(con):
    a = run_tool(con, "draft_reply", {"email_id": 1, "body": "ok"})
    b = run_tool(con, "draft_reply", {"email_id": 1, "body": "ok"})
    assert a == b and len(mailbox.snapshot(con)["drafts"]) == 1


def test_send_needs_approval_and_is_idempotent(con):
    run_tool(con, "draft_reply", {"email_id": 1, "body": "ok"})
    assert run_tool(con, "send_draft", {"draft_id": 1}).startswith("refused")          # no approver
    assert run_tool(con, "send_draft", {"draft_id": 1}, approve=lambda *a: False).startswith("refused")
    assert mailbox.snapshot(con)["sent"] == []
    assert run_tool(con, "send_draft", {"draft_id": 1}, approve=lambda *a: True).startswith("ok")
    assert "already sent" in run_tool(con, "send_draft", {"draft_id": 1}, approve=lambda *a: True)
    assert len(mailbox.snapshot(con)["sent"]) == 1


def test_reset_restores_the_seed(con, tmp_path):
    run_tool(con, "label_email", {"email_id": 1, "label": "spam", "folder": "archive"})
    con2 = mailbox.reset(tmp_path / "m.db", SEED)
    assert mailbox.snapshot(con2)["emails"][0] == {"id": 1, "folder": "inbox", "labels": ""}
