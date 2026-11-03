"""LLM judge for correctness and faithfulness, with an on-disk cache.

The cache key is (model, prompt), so re-running an eval or comparing two
configurations never pays twice for the same judgement.
"""
import hashlib
import json
from pathlib import Path

from src import config
from src.generate import chat

CACHE = Path(__file__).resolve().parents[1] / "results" / "cache"

CORRECTNESS = """You grade answers to questions about Tunisian law. Compare the candidate answer with the reference answer.
Mark it correct if it states the same key facts (numbers, delays, authorities, conditions) as the reference, even if worded differently or in another language. Extra correct detail is fine. A missing key fact, a wrong number, or an "I don't know" is incorrect.
Reply with JSON only: {"correct": true|false, "reason": "<one short sentence>"}

Question: %(question)s
Reference answer: %(reference)s
Candidate answer: %(answer)s"""

FAITHFULNESS = """You check whether an answer is supported by the sources it cites.
Go through every factual claim in the answer. A claim is supported only if the cited sources state it. Claims that need outside knowledge are unsupported.
Reply with JSON only: {"faithful": true|false, "unsupported": ["<claim>", ...]}

Sources:
%(sources)s

Answer: %(answer)s"""


def _call(prompt, model):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    text, usage = chat([{"role": "user", "content": prompt}], model=model, max_tokens=300)
    out = {"text": text, "usage": usage}
    f.write_text(json.dumps(out, ensure_ascii=False))
    return out


def _parse(text):
    start, end = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[start:end + 1])
    except (ValueError, json.JSONDecodeError):
        return {}


def judge_correct(question, reference, answer, model=None):
    r = _call(CORRECTNESS % {"question": question, "reference": reference, "answer": answer}, model or config.JUDGE)
    v = _parse(r["text"])
    return bool(v.get("correct")), v.get("reason", ""), r["usage"]["cost_usd"]


def judge_faithful(answer, cited_chunks, numbers=None, model=None):
    """Is every claim supported by the sources the answer cites?

    numbers: the [n] each chunk had in the prompt. The answer cites those numbers, so the judge must see
    the same ones (numbering them 1..k by position would make `[3]` point at the wrong source).
    """
    numbers = list(numbers) if numbers is not None else range(1, len(cited_chunks) + 1)
    sources = "\n\n".join(f"[{n}] {c['text']}" for n, c in zip(numbers, cited_chunks))
    r = _call(FAITHFULNESS % {"sources": sources, "answer": answer}, model or config.JUDGE)
    v = _parse(r["text"])
    return bool(v.get("faithful")), v.get("unsupported", []), r["usage"]["cost_usd"]
