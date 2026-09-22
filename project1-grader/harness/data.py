"""Read/write helpers for the jsonl files under data/ and results/."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from harness.config import CANDIDATES_PATH, DB_PATH, GOLDEN_PATH, QUERIES_PATH


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_queries(split: str | None = None) -> list[dict]:
    rows = read_jsonl(QUERIES_PATH)
    if not rows:
        raise SystemExit(f"{QUERIES_PATH} missing — run `python data/make_queries.py`.")
    return [r for r in rows if split in (None, "all", r["split"])]


def load_candidates() -> list[dict]:
    rows = read_jsonl(CANDIDATES_PATH)
    if not rows:
        raise SystemExit(f"{CANDIDATES_PATH} missing — run `python -m harness.candidates`.")
    return rows


def load_golden(split: str | None = None) -> list[dict]:
    rows = read_jsonl(GOLDEN_PATH)
    if not rows:
        raise SystemExit(f"{GOLDEN_PATH} missing — label the candidates, then run "
                         f"`python -m harness.golden`.")
    return [r for r in rows if split in (None, "all", r["split"])]


def preview_result(sql: str, limit: int = 5) -> tuple[list[str], list[tuple], int]:
    """Run a query and return (column names, first `limit` rows, total row count).
    Used by the labelling tool so labellers can check claims against real data."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()
    return cols, rows[:limit], len(rows)
