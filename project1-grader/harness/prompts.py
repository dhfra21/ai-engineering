"""Load versioned prompt files from prompts/<kind>/<version>.md.

File format — two sections, each introduced by a line that is exactly the
marker, everything else is literal text:

    <!-- system -->
    ...system message...
    <!-- user -->
    ...user message, with {{placeholders}}...

Anything before the first marker (e.g. a comment describing the version) is
ignored. Placeholders use {{name}} rather than str.format braces because the
prompts contain SQL and JSON. An unfilled or unknown placeholder is an error,
not a silent blank.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from harness.config import PROMPTS_DIR

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


@dataclass(frozen=True)
class Prompt:
    kind: str
    version: str
    system: str
    user: str

    @property
    def sha(self) -> str:
        return hashlib.sha256((self.system + "\0" + self.user).encode()).hexdigest()[:10]

    @property
    def tag(self) -> str:
        return f"{self.kind}/{self.version}"

    def render(self, **values: str) -> list[dict]:
        wanted = set(_PLACEHOLDER.findall(self.system + self.user))
        missing = wanted - set(values)
        unknown = set(values) - wanted
        if missing or unknown:
            raise KeyError(f"{self.tag}: missing={sorted(missing)} unknown={sorted(unknown)}")

        def fill(text: str) -> str:
            return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), text)

        return [
            {"role": "system", "content": fill(self.system).strip()},
            {"role": "user", "content": fill(self.user).strip()},
        ]


def load(kind: str, version: str) -> Prompt:
    path = PROMPTS_DIR / kind / f"{version}.md"
    if not path.exists():
        available = sorted(p.stem for p in (PROMPTS_DIR / kind).glob("*.md"))
        raise FileNotFoundError(f"No prompt {path}. Available for '{kind}': {available}")
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^<!-- (system|user) -->\s*$", text, flags=re.MULTILINE)
    sections = dict(zip(parts[1::2], parts[2::2]))
    if set(sections) != {"system", "user"}:
        raise ValueError(f"{path}: needs exactly one '<!-- system -->' and one '<!-- user -->' marker")
    return Prompt(kind=kind, version=version, system=sections["system"], user=sections["user"])
