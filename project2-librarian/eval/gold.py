"""Decide whether a retrieved chunk contains the gold passage of a question."""
import json
import re
from pathlib import Path

QA = Path(__file__).resolve().parents[1] / "data" / "eval" / "qa.jsonl"


def load_qa(answerable_only=False):
    rows = [json.loads(l) for l in QA.open()]
    return [r for r in rows if r["answerable"]] if answerable_only else rows


def _squash(s):
    return re.sub(r"\s+", "", s)


def article_numbers(label):
    nums = {int(n) for n in re.findall(r"\d+", label)}
    if re.search(r"premier|unique|الأول|الوحيد", label):
        nums.add(1)
    return nums


def is_gold(chunk, item):
    """Same law, and either the chunk's article label names the gold article
    (works across languages) or it contains the start/end of the evidence text
    (works for fixed-size chunks that have no article label)."""
    if chunk["doc_id"] != item["gold_doc"]:
        return False
    if set(item["gold_articles"]) & article_numbers(chunk["article"]):
        return True
    ev = _squash(item["evidence"])
    body = _squash(chunk["text"])
    return len(ev) >= 30 and (ev[:50] in body or ev[-50:] in body)
