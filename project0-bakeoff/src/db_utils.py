"""Safe, read-only SQLite execution + result-set comparison.

Kept deliberately dumb: this is a Project 0 eval harness, not the
Text2SQL agent's validate_sql() tool. It still refuses to run anything
that isn't a single SELECT, because model output is untrusted text and
this script executes it against a real (if disposable) database file.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|ATTACH|PRAGMA|VACUUM|EXEC)\b",
    re.IGNORECASE,
)


@dataclass
class ExecResult:
    ok: bool
    columns: list[str]
    rows: list[tuple]
    error: str | None


def clean_sql(raw: str) -> str:
    """Strip markdown code fences / stray prose the model may add despite
    instructions. Best-effort only — does not change what counts as a
    parse failure downstream."""
    text = raw.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()


def is_single_select(sql: str) -> bool:
    stripped = sql.strip().rstrip(";").strip()
    if ";" in stripped:
        return False  # multiple statements
    if _FORBIDDEN.search(stripped):
        return False
    return bool(re.match(r"^\s*(SELECT|WITH)\b", stripped, re.IGNORECASE))


def execute_readonly(db_path: str, sql: str, timeout_s: float = 5.0) -> ExecResult:
    cleaned = clean_sql(sql)
    if not is_single_select(cleaned):
        return ExecResult(ok=False, columns=[], rows=[], error="rejected: not a single read-only SELECT")

    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=timeout_s)
        conn.execute("PRAGMA query_only = TRUE;")
        cur = conn.cursor()
        cur.execute(cleaned)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        return ExecResult(ok=True, columns=cols, rows=rows, error=None)
    except sqlite3.Error as e:
        return ExecResult(ok=False, columns=[], rows=[], error=str(e))
    except Exception as e:  # noqa: BLE001 — never let a bad model output crash the run
        return ExecResult(ok=False, columns=[], rows=[], error=f"unexpected error: {e}")


def _normalize_cell(v, ndigits: int = 2):
    if isinstance(v, float):
        return round(v, ndigits)
    if isinstance(v, str):
        return v.strip()
    return v


def rows_match(gold_rows: list[tuple], pred_rows: list[tuple], ndigits: int = 2) -> bool:
    """Execution-accuracy comparison: same rows, ignoring row order and
    float rounding noise, but respecting duplicates (multiset, not set)."""
    norm_gold = sorted(
        tuple(_normalize_cell(c, ndigits) for c in row) for row in gold_rows
    )
    norm_pred = sorted(
        tuple(_normalize_cell(c, ndigits) for c in row) for row in pred_rows
    )
    return norm_gold == norm_pred
