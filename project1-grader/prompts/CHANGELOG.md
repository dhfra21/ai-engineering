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
| v1 | Rubric condensed from LABELLING_GUIDE v1; reason before grade; explicit "length is not quality" | — | — → 53/60 (88.3%) / κ 0.768 / bad caught 27/33, precision 27/28. (54/60 against the labels before guide v3; most of its disagreements turned out to be label errors, see postmortem) | `results/judge/v1_gptoss120b_dev` |
| v2 | Synced to guide v3: rules 3.10–3.12 written out, rule 3.1 (silence is fine) made explicit, clause-by-clause restatement fails "clear" | v1 missed "each category" over inner joins (c-q046, c-q098, c-q099) and a planted jargon error (c-q140), and failed c-q083 for silence | 53/60 → 53/60 (88.3%) / κ 0.765 / bad caught 27/33 → 29/33, precision 27/28 → 29/32. Fixed c-q046, c-q098; now over-applies rule 3.12 to "for each product" (c-q127) and fails c-q126 for an ordering detail; c-q083, c-q099 and c-q140 still wrong. A tie, not an improvement. **Chosen** for its higher recall and because it states the rules the labels use | `results/judge/v2_gptoss120b_dev` |
