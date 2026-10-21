# Postmortem: Project 1

_Write this as a team after the final runs. The brief: "A postmortem with no
problems loses points." For each problem, say what happened, how you found
out (ideally with a number or an item id), what you changed, and what you'd
do differently._

## What went wrong

### Labelling
- **AI labellers instead of two humans** (instructor-approved): two separate
  Claude Opus 5.5 subagents, each with a blind packet (guide + what the human
  tool shows, own shuffled order, no sources, no access to the other's file);
  humans adjudicate the disagreements. Two copies of one model are not
  independent the way two people are: they share blind spots, so raw
  agreement likely overstates how clear the guide is. Report it that way.
- **We first tried Groq models as labellers and abandoned it.** qwen3.8-27b
  and gpt-oss-20b (high reasoning) worked (5/5 agreed, both caught a planted
  join error), but each call is ~2,900 input tokens (the guide is ~2,300)
  against a free-tier cap of 200K tokens/day/model, i.e. ~3 days, and the
  judge needs that quota. Groq's prompt caching did not discount the repeated
  guide prefix (tested 2026-10-06). gpt-oss-20b would also have graded its
  own answers.
- **Agreement was 157/161 (97.5%, κ 0.947), and that hides label errors.**
  Both labellers passed 4 of 55 planted errors. Three are defensible (c-q063's
  "error" changed nothing; c-q124 and c-q152 are loose wording the rest of the
  explanation corrects), but c-q102 drops the sort order, which rule 3.3
  requires, and labeller B's note even quotes "most first", which isn't in
  the text. Agreement measures consistency, not correctness; two copies of a
  model agree on the same misses. We corrected c-q102 via
  `data/labels/overrides.jsonl`.
- **Adjudication was done by Claude, not people**, at the team's request:
  all 4 disagreements went to bad (correct), and guide v2 added rules 3.10
  (stated mechanism must be true) and 3.11 ("all" must mean all).
- **Label fixes kept coming after the golden set was "frozen".** The gpt-5-mini
  judge exposed three more dev label errors on 2026-10-20: c-q145 ("lists
  every order" over an inner join, the rule-3.12 pattern the sweep had
  missed for the third time after c-q108 and c-q095), c-q130 ("purchased"
  with no status filter: 40 products qualify vs 35 with completed orders
  only) and c-q107 (an order promised with no ORDER BY, rule 3.3). Golden
  set 85/76 -> 82/79. These were fixed on dev only; see "The judge" for
  what that did to the dev/test comparison.

### The judge
- **The judge found label errors before we found judge errors.** Judge v1 on
  dev disagreed 6 times, 5 of them stricter than the labels. On 4 of those,
  re-reading the guide showed the judge was right: "lists every customer"
  over an inner join (c-q020, c-q111, and "each category" c-q097) and a
  missing output column (c-q128). We wrote rule 3.12 for the first pattern
  and swept all 161 items for it, test included, before the judge had seen
  test: 10 labels changed good -> bad. The column omission was fixed only
  where found, so others may remain. Risk to report: these fixes were
  prompted by the judge, which nudges dev agreement up (v1 went from 54/60
  to 55/60 on the corrected labels). The sweep over test is by rule, not by
  judge output.
- **Dev agreement overstated the judge: 54/60 (90%, κ 0.79) on dev,
  65/101 (64%, κ 0.33) on test.** Two causes. (1) Dev labels were corrected
  wherever the judge disagreed, test labels were not (they can't be now
  without relabelling after seeing judge verdicts). Several test
  disagreements are exactly the patterns we fixed on dev: "purchased /
  bought / sold" with no status filter (c-q035, c-q037, c-q136, c-q146) and
  "every order" over an inner join (c-q050, c-q156). (2) The judge is
  genuinely too strict: roughly 23 of its 33 false "bad" calls on test
  demand things rule 3.1/3.2 say may be left out: rows merged by GROUP BY
  name (c-q026, c-q029, c-q038, c-q044), exclusions the explanation never
  denies (c-q018, c-q043, c-q123, c-q137, c-q148), default ascending sort
  (c-q060, c-q118), rounding, currency (c-q053). Precision of "bad" is
  40/73 (55%) on test; hard items agree 14/36.
- **It catches planted errors but misses jargon.** Planted errors caught on
  test: invented_detail 7/7, missing_condition 7/7, wrong_filter 5/5,
  wrong_join_semantics 6/6, wrong_aggregation 4/4, jargon 5/6. The
  clause-by-clause jargon rewrite was missed on dev (c-q140) and test
  (c-q120) by both judge versions on both providers.
- **We switched judge model mid-project.** All judge and bias numbers before
  2026-10-20 are on Groq gpt-oss-120b and are not comparable with the
  gpt-5-mini ones. Judge v2 (chosen on Groq for recall) tied v1 on
  gpt-5-mini at 54/60 but marked more good answers bad (precision 36/42 vs
  34/38), so we went back to v1.

### The harness / infrastructure
- **The weak-candidate model disappeared.** `llama-3.1-8b-instant` returned
  404 for our key on 2026-10-06 (Groq's docs still listed it). allam-2-7b
  failed JSON output 4/4, so we used qwen3.8-27b, which writes good answers:
  most bad candidates are planted errors, not natural mistakes.
- **One candidate failed generation**: q145, invalid JSON from gpt-oss-20b;
  a cached rerun retried only that call and it succeeded.
- **Windows bugs found on first real run**: the mock test assumed
  `data/labels/` existed, and report printing crashed on cp1252 consoles.
- **The Groq free tier was the bottleneck, not our code.** The cap is
  200K tokens/day per model per *organization* (a second key in the same
  account shares it), and it is a rolling window, so tokens return slowly.
  Position bias (step 6) stopped at 83/101 on the first key and finished on
  a key from a second account; verbosity-template (step 7) then stopped at
  32/101 on that key. Steps 7 to 9 need roughly a week of one key, so we
  split them across teammates' own accounts. Cached calls are not in git
  (`.cache/` is ignored), so a teammate cannot resume another machine's
  partial run.
- **We moved from Groq to OpenAI** on 2026-10-20, using a key the instructor
  provided. No daily cap, so steps 6-9 ran in about a day. Model mapping:
  gpt-5-nano (system), gpt-5-mini (judge, perturber), gpt-4o-mini (weak
  candidates). The change was small because the harness already spoke the
  OpenAI chat format; the gpt-5 models reject `temperature`, which needed a
  per-model flag.
- **Token budgets were too small for reasoning models.** The judge hit its
  1,536-token cap on 3/60 dev items (fixed: 4,096); system v3 hit its
  1,024-token cap on q159 in both dev runs (raised to 2,048 for test; one
  answer, q096, still hit 2,048 in an aborted run). Truncation shows up as
  an error row, never as a guessed grade.
- **Runs are not repeatable.** gpt-5 models take no temperature, so two
  identical v1 dev runs scored 43 and 40 with 19 items flipping. We only
  noticed after reading v2's 18 flips as an effect. Every prompt comparison
  after that used two uncached runs, and the test score is three runs.
- **`--no-cache` overwrites the cache**, so an interrupted repeat run can't
  be resumed without mixing two samples; we restarted test run 3 from
  scratch.

### The system prompt
- **v2 (row scope) did nothing measurable**: 43/60 -> 43/60 with 9 flips each
  way, the same size as rerun noise. It fixed the inner-join wording it
  targeted but the longer answers started inventing row orders ("order
  preserved as in the table", c-q075; "stable order", c-q127).
- **v3 (row order only from ORDER BY) is the one real gain**: 51/59 and 47/59
  vs v1's 43/60 and 40/60, so both v3 runs beat both v1 runs. Test, three
  runs: 78, 76, 80 of 101 (mean 77.2%). Hard queries remain weak (20-26 of
  36) and vary most between runs.

## What we learned

- **Agreement between two copies of one model measures consistency, not
  correctness.** 97.5% labeller agreement still hid at least 17 label
  errors, most found by the judge.
- **Fixing labels where the judge disagrees inflates judge agreement.** Our
  dev number (90%) is not the judge's reliability; the untouched test split
  (64%) is closer to it.
- **One run is not a measurement** with models that ignore temperature.
  Rerun noise (about 15-19 flips on 60 items) was as large as the effect we
  were trying to measure.
- **Template padding is the only clean verbosity test.** The LLM pad model
  repaired the answers it was told only to lengthen (c-q027, c-q086, c-q089,
  c-q150).
- **The harness choices paid off**: strict schemas plus error rows meant no
  silent zeros; the cache made every interruption cheap; switching provider
  touched two files.

## What we'd do differently next time (Projects 2, 3 and 5 reuse this harness)

- **Fix labels by rule, blind to the judge, on both splits at once**, or
  hold out a second test set the judge never influences.
- **Use human labellers for at least a sample**, to measure how much two
  copies of one model share blind spots.
- **Plan for repeated runs from the start**: store a run index in the cache
  key so repeats don't overwrite each other and can resume.
- **Size token budgets for reasoning models up front**, and log reasoning
  tokens separately from answer tokens.
- **Write a judge prompt that enforces rule 3.1 ("silence is fine")** and
  catches clause-by-clause jargon, then measure it on a split whose labels
  it never influenced.
