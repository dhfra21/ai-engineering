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
- _e.g. disagreements concentrated on rule X; guide v1 → v2 changed …;
  raw κ was _ before adjudication_

### The judge
- _e.g. it misses `wrong_join_semantics` errors: _/_ caught on golden-test;
  item ids …_

### The harness / infrastructure
- **The weak-candidate model disappeared.** `llama-3.1-8b-instant` returned
  404 for our key on 2026-10-06 (Groq's docs still listed it). allam-2-7b
  failed JSON output 4/4, so we used qwen3.8-27b, which writes good answers:
  most bad candidates are planted errors, not natural mistakes.
- **One candidate failed generation**: q145, invalid JSON from gpt-oss-20b;
  a cached rerun retried only that call and it succeeded.
- **Windows bugs found on first real run**: the mock test assumed
  `data/labels/` existed, and report printing crashed on cp1252 consoles.
- _e.g. hit the Groq daily cap on day N; json_schema fallback triggered for
  model …; N schema violations_

### The system prompt
- _e.g. v3 fixed LIMIT omissions but made explanations more technical
  (clear failures _ → _)_

## What we learned

-

## What we'd do differently next time (Projects 2, 3 and 5 reuse this harness)

-
