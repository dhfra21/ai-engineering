"""The system under test: SQL query in, plain-language explanation out.

It only ever sees the schema and the SQL — never the query's `intent` or
`watch_for` fields, which are reference material for labellers and the judge.
"""
from __future__ import annotations

from harness import prompts
from harness.config import MAX_TOKENS, SCHEMA_TEXT, SYSTEM_MODEL
from harness.llm import LLMResult, call_json


def explain(sql: str, prompt_version: str, model_key: str = SYSTEM_MODEL,
            use_cache: bool = True) -> LLMResult:
    prompt = prompts.load("system", prompt_version)
    messages = prompt.render(schema=SCHEMA_TEXT, sql=sql)
    return call_json(model_key, messages, "system", MAX_TOKENS["system"], use_cache=use_cache)
