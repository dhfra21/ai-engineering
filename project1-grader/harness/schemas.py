"""The fixed JSON schemas every model call must answer in, plus a small
validator. Groq enforces the schema server-side in strict mode; we validate
again locally anyway, because (a) json_object-mode models are not enforced
and (b) scoring must never depend on trusting the provider.

Strict mode requires every property to be listed in `required` and
`additionalProperties: false`, so all schemas follow that shape.
"""
from __future__ import annotations

from typing import Any

CRITERIA = ["correct", "complete", "no_invention", "clear"]

SYSTEM = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string", "minLength": 1},
    },
    "required": ["explanation"],
    "additionalProperties": False,
}

# `reason` comes first so the model writes its justification before the grade.
JUDGE = {
    "type": "object",
    "properties": {
        "reason": {"type": "string", "minLength": 1},
        "failed_criteria": {"type": "array", "items": {"type": "string", "enum": CRITERIA}},
        "grade": {"type": "string", "enum": ["good", "bad"]},
    },
    "required": ["reason", "failed_criteria", "grade"],
    "additionalProperties": False,
}

PAIRWISE = {
    "type": "object",
    "properties": {
        "reason": {"type": "string", "minLength": 1},
        "winner": {"type": "string", "enum": ["A", "B", "tie"]},
    },
    "required": ["reason", "winner"],
    "additionalProperties": False,
}

PERTURB = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string", "minLength": 1},
        "change_made": {"type": "string", "minLength": 1},
    },
    "required": ["explanation", "change_made"],
    "additionalProperties": False,
}

PAD = SYSTEM  # a padded explanation has the same shape as a normal one

BY_NAME = {"system": SYSTEM, "judge": JUDGE, "pairwise": PAIRWISE, "perturb": PERTURB, "pad": PAD}


class SchemaError(ValueError):
    pass


def validate(value: Any, schema: dict, path: str = "$") -> None:
    """Supports exactly the subset of JSON Schema used above. Raises SchemaError."""
    t = schema.get("type")
    if t == "object":
        if not isinstance(value, dict):
            raise SchemaError(f"{path}: expected object, got {type(value).__name__}")
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                raise SchemaError(f"{path}: missing required key '{key}'")
        if schema.get("additionalProperties") is False:
            extra = set(value) - set(props)
            if extra:
                raise SchemaError(f"{path}: unexpected keys {sorted(extra)}")
        for key, sub in props.items():
            if key in value:
                validate(value[key], sub, f"{path}.{key}")
    elif t == "array":
        if not isinstance(value, list):
            raise SchemaError(f"{path}: expected array, got {type(value).__name__}")
        for i, item in enumerate(value):
            validate(item, schema.get("items", {}), f"{path}[{i}]")
    elif t == "string":
        if not isinstance(value, str):
            raise SchemaError(f"{path}: expected string, got {type(value).__name__}")
        if len(value.strip()) < schema.get("minLength", 0):
            raise SchemaError(f"{path}: string too short")
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaError(f"{path}: {value!r} not in {schema['enum']}")
