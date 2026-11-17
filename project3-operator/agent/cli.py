"""Interactive use: python -m agent.cli "archive the newsletters and draft a reply to DF"."""
import sys

from sandbox import mailbox

from . import config
from .loop import run


def ask_human(name, args, preview):
    print(f"\n--- The agent wants to run {name}({args}) ---\n{preview}\n")
    return input("Approve? [y/N] ").strip().lower() == "y"


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "Triage my inbox."
    con = mailbox.reset()
    t = run(task, con, approve=ask_human)
    for s in t.steps:
        print(f"- {s['tool']}({s['args']}) -> {s['result'][:100]}")
    print(f"\n{t.final}\n[stop: {t.stop_reason}, {len(t.steps)} steps, ${t.cost:.4f}]")
