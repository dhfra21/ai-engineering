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
System gpt-5-nano, judge v1 on gpt-5-mini, dev (60 items). **Neither model accepts
`temperature`, so runs are not repeatable:** two identical v1 runs scored 43 and
40 with 19 items flipping. A version only counts as better if it beats the
baseline across reruns, not by one run's flips.

| Version | Change (one idea per version) | Why (which failures in the previous run) | Dev before → after | Items that flipped | Run ids |
|---|---|---|---|---|---|
| v1 | Baseline: "explain in plain words", nothing else | — | — → 43/60 (71.7%); uncached rerun 40/60 (66.7%), 19 items flipped between the two | — | `20261020-173910`, rerun `20261020-233804` |
| v2 | Be exact about which rows the result covers: plain JOIN drops unmatched rows; no invented status filter | v1's most common failure (7/17): "every order / all products" over an inner join (q108, q145, q158, q161, q135), "completed / sold" with no status filter (q024, q134) | 43/60 → 43/60 (71.7%) | bad→good (9): q020, q024, q055, q082, q108, q134, q135, q158, q161; good→bad (9): q005, q023, q040, q054, q075, q098, q113, q126, q127 | `20261020-231149` |
| v3 | v2 + describe row order only from ORDER BY: name each sort key and its direction; say nothing about order without ORDER BY | Order failures in v1 (q046, q154 missing direction; q107 order promised without ORDER BY) and new ones v2 introduced ("order preserved as in the table" q075, "stable order" q127, non-alphabetical example q023) | 43/60 → 51/59 (86.4%); uncached rerun 47/59 (79.7%), 14 flips | vs v2: bad→good (12): q005, q023, q040, q046, q054, q075, q097, q107, q113, q127, q145, q154; good→bad (4): q082, q087, q125, q130. q159 errored in both runs (answer hit the 1,024-token cap) | `20261020-232532`, rerun `20261020-235312` |

Reading: v2 is **no change**. Its 18 flips are the same size as the noise between two identical v1 runs (19), so it neither helped nor hurt; the row-scope items it fixed went back and forth in the v1 reruns too. v3 is a **real improvement**: both v3 runs (51, 47) beat both v1 runs (43, 40), by about 8 items (~14 points) on average. v3 is the version to report.

**Reported test score, system v3 (judge v1 on gpt-5-mini), 3 runs, 2026-10-21:**
78/101 (77.2%), 76/101 (75.2%), 80/101 (79.2%). Mean 78.0/101 (77.2%), range
75.2–79.2%. Hard queries vary most across runs (21, 20, 26 of 36). For the test
runs the system's `max_completion_tokens` was raised from 1,024 to 2,048, because
v3 hit the cap on q159 in both dev runs; none of the three test runs was cut off.
Run ids `20261021-080824`, `20261021-083154`, `20261021-101225`.

## Judge prompt

Changes to the judge are measured by **agreement with humans on golden-dev**
(`python -m harness.judge_eval --split dev --judge vN`), not by the system's
score.

| Version | Change | Why | Agreement / κ / bad caught (dev) before → after | Run dir |
|---|---|---|---|---|
| v1 | Rubric condensed from LABELLING_GUIDE v1; reason before grade; explicit "length is not quality" | — | — → 53/60 (88.3%) / κ 0.768 / bad caught 27/33, precision 27/28. (54/60 against the labels before guide v3; most of its disagreements turned out to be label errors, see postmortem) | `results/judge/v1_gptoss120b_dev` |
| v2 | Synced to guide v3: rules 3.10–3.12 written out, rule 3.1 (silence is fine) made explicit, clause-by-clause restatement fails "clear" | v1 missed "each category" over inner joins (c-q046, c-q098, c-q099) and a planted jargon error (c-q140), and failed c-q083 for silence | 53/60 → 53/60 (88.3%) / κ 0.765 / bad caught 27/33 → 29/33, precision 27/28 → 29/32. Fixed c-q046, c-q098; now over-applies rule 3.12 to "for each product" (c-q127) and fails c-q126 for an ordering detail; c-q083, c-q099 and c-q140 still wrong. A tie, not an improvement. Chosen for its higher recall and because it states the rules the labels use (superseded by the gpt-5-mini rows below) | `results/judge/v2_gptoss120b_dev` |

**Judge model changed to gpt-5-mini (OpenAI), 2026-10-20.** The Groq rows above
are on a different judge and against older labels, so they are not comparable
with the rows below. Same prompt files; scored against the golden set after
the c-q145, c-q130 and c-q107 overrides (82 good / 79 bad).

| Version | Model | Agreement / κ / bad caught / precision of bad (dev) | Notes | Run dir |
|---|---|---|---|---|
| v1 | gpt-5-mini | 54/60 (90.0%) / κ 0.789 / 34/36 / 34/38 | Wrong on c-q083, c-q126 (fails for silence), misses the planted jargon error c-q140 again; c-q014 and c-q127 borderline. **Chosen** for steps 6–9: fewest good answers marked bad, so the system score is least understated | `results/judge/v1_gpt5mini_dev` |
| v2 | gpt-5-mini | 54/60 (90.0%) / κ 0.783 / 36/36 / 36/42 | Catches every bad answer and fixes c-q140, but over-applies rule 3.12 to "each month / each day" (c-q030, c-q112) and fails c-q106 for not mentioning order. A tie on agreement, lower precision | `results/judge/v2_gpt5mini_dev` |
