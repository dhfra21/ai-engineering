# Prompt changelog

Every prompt change gets an entry here, and every entry links the change to
a score before and after. `python -m harness.run` prints the before/after
and the exact items that flipped. Paste them in.

Rules:
- Tune on **dev**. Put a test score in this file only for versions you
  report.
- Only compare runs that use the same judge prompt (`judge_sha` in
  `results/history.csv`). If the judge changes, the scores are on a new
  scale, so re-run the baseline with the new judge first.
- Never edit a published version file. Copy it to a new version instead.
  The sha in `history.csv` will catch you if you do.
- Include changes that made things worse. A changelog where every change is
  an improvement is not believable.

## System prompt

| Version | Change (one idea per version) | Why (which failures in the previous run) | Dev before → after | Items that flipped | Run ids |
|---|---|---|---|---|---|
| v1 | Baseline: "explain in plain words", nothing else | — | — → _/60 | — | _ |
| v2 | _ | _ | _/60 → _/60 | bad→good: _ ; good→bad: _ | _ |

## Judge prompt

Changes to the judge are measured by **agreement with humans on golden-dev**
(`python -m harness.judge_eval --split dev --judge vN`), not by the system's
score.

| Version | Change | Why | Agreement / κ / bad caught (dev) before → after | Run dir |
|---|---|---|---|---|
| v1 | Rubric condensed from LABELLING_GUIDE v1; reason before grade; explicit "length is not quality" | — | — → _ | _ |
