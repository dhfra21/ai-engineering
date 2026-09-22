# Report outline → report.pdf (max 4 pages)

These are the brief's six sections, with where each number comes from.
Give counts and percentages everywhere.

## 1. The task, and why exact match isn't enough (~½ page)
- Input: a SQL query. Output: a plain-language explanation for a non-SQL
  reader.
- Show one query with two good explanations that share almost no words, and
  one fluent wrong one that overlaps heavily with a good one. That's the
  argument against exact match and word overlap.

## 2. The golden set (~¾ page)
- Where the 161 queries came from: 50 from Project 0, 111 new ones aimed at
  traps. All verified against the DB. Split 60/101, stratified.
- Where the candidates came from: baseline / weak / perturbed, with counts
  and why we mixed them. Labellers never saw the source.
- The labelling guide in one paragraph: four criteria, and the rules you
  argued about.
- **Agreement:** raw agreement, Cohen's κ, the confusion matrix, and
  agreement by difficulty and by source (`results/labels/agreement.md`).
  Items dropped and why. How many were adjudicated, and which guide rules
  changed as a result.

## 3. The harness (~½ page)
- The one command, what one row looks like, and the fixed JSON schemas.
  Validation plus one retry means failures show up as errors instead of
  being parsed from text.
- Caching, resuming after the free-tier cap, and the mock backend and tests.

## 4. The judge: reliability report (~1 page)
- Agreement with humans on golden-**test**: count, %, 95% CI, κ, recall and
  precision of "bad".
- Breakdown by planted error type. Which mistakes does the judge miss?
- **Position bias:** flip rate, first-slot win rate, and whether the judge
  picks the unbroken original on known-better pairs.
- **Verbosity bias:** template padding and LLM padding. Grade changes, and
  human-bad answers rescued by padding. Pairwise original vs padded.
- **Where the judge fails:** a specific list with example item ids. This is
  what demo day will probe.

## 5. The system: score history (~½ page)
- A table built from CHANGELOG.md: version → dev score → items flipped, and
  the test score for the versions you report.
- One or two sentences per change on why it helped or hurt.

## 6. Cost model (~¼ page)
- From `python -m harness.cost`: tokens and $ per request (system) and per
  judged item. Cost per 1k requests, today and at 100×, with the traffic
  assumption stated. Note that reasoning tokens are billed, and say where
  the free tier stops being enough.
- Judge latency p50/p95 per item.
