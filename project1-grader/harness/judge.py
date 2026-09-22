"""The LLM judge. Two modes:

- grade():   one explanation -> {reason, failed_criteria, grade: good|bad}.
             This is what scores the system and what we check against humans.
- compare(): two explanations -> {reason, winner: A|B|tie}. Only used for the
             position- and verbosity-bias checks (harness/bias.py).

The judge sees the same reference material the human labellers see (the
query's intent and, when present, its watch_for note) so that judge/human
agreement compares like with like. It never sees where a candidate came from.
"""
from __future__ import annotations

from harness import prompts
from harness.config import JUDGE_MODEL, MAX_TOKENS, SCHEMA_TEXT
from harness.llm import LLMResult, call_json


def _reference(query: dict) -> dict:
    return {
        "schema": SCHEMA_TEXT,
        "sql": query["sql"],
        "intent": query["intent"],
        "watch_for": query.get("watch_for") or "(nothing specific)",
    }


def grade(query: dict, explanation: str, prompt_version: str, model_key: str = JUDGE_MODEL,
          use_cache: bool = True) -> LLMResult:
    prompt = prompts.load("judge", prompt_version)
    messages = prompt.render(**_reference(query), explanation=explanation)
    return call_json(model_key, messages, "judge", MAX_TOKENS["judge"], use_cache=use_cache)


def compare(query: dict, explanation_a: str, explanation_b: str, prompt_version: str,
            model_key: str = JUDGE_MODEL, use_cache: bool = True) -> LLMResult:
    prompt = prompts.load("judge_pairwise", prompt_version)
    messages = prompt.render(**_reference(query), explanation_a=explanation_a,
                             explanation_b=explanation_b)
    return call_json(model_key, messages, "pairwise", MAX_TOKENS["pairwise"], use_cache=use_cache)


def score_of(result: LLMResult) -> int | None:
    """1 = good, 0 = bad, None = the judge call failed (reported separately,
    never folded into the score)."""
    if not result.ok:
        return None
    return 1 if result.data["grade"] == "good" else 0
