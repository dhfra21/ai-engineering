"""The test environment: a SQLite mailbox of fake emails. Nothing here touches a real account.

`reset()` rebuilds it from sandbox/seed.json, so every eval scenario starts from the same state.
"Sent" mail is only a row in the `sent` table: there is no SMTP code anywhere in this repo.
"""
import json
import sqlite3
from pathlib import Path

from agent import config

SCHEMA = """
CREATE TABLE emails (id INTEGER PRIMARY KEY, sender TEXT, subject TEXT, body TEXT, received TEXT,
                     folder TEXT DEFAULT 'inbox', labels TEXT DEFAULT '');
CREATE TABLE drafts (id INTEGER PRIMARY KEY AUTOINCREMENT, email_id INTEGER, body TEXT, idem_key TEXT UNIQUE);
CREATE TABLE sent   (id INTEGER PRIMARY KEY AUTOINCREMENT, draft_id INTEGER UNIQUE, to_addr TEXT, body TEXT);
"""


def connect(path=None):
    con = sqlite3.connect(path or config.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def reset(path=None, seed=None):
    """Delete the database and rebuild it from the seed file (or a list of email dicts)."""
    path = Path(path or config.DB_PATH)
    path.unlink(missing_ok=True)
    con = connect(path)
    con.executescript(SCHEMA)
    emails = seed if seed is not None else json.loads(config.SEED_PATH.read_text())
    for e in emails:
        con.execute("INSERT INTO emails (id, sender, subject, body, received, folder, labels) VALUES (?,?,?,?,?,?,?)",
                    (e["id"], e["sender"], e["subject"], e["body"], e.get("received", ""),
                     e.get("folder", "inbox"), e.get("labels", "")))
    con.commit()
    return con


def snapshot(con):
    """Everything the agent could have changed, for the eval to compare with the expected end state."""
    return {
        "emails": [dict(r) for r in con.execute("SELECT id, folder, labels FROM emails ORDER BY id")],
        "drafts": [dict(r) for r in con.execute("SELECT email_id, body FROM drafts ORDER BY id")],
        "sent": [dict(r) for r in con.execute("SELECT to_addr, body FROM sent ORDER BY id")],
    }


if __name__ == "__main__":
    reset()
    print(f"sandbox reset: {config.DB_PATH}")
