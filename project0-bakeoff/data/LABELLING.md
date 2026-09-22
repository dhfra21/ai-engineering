# How `items.jsonl` was built and checked

## Source

All 50 items are hand-written against the mini retail database defined in
`db/schema.sql` and seeded deterministically by `db/build_db.py`
(`random.seed(42)`; 30 customers, 8 categories, 40 products, 160 orders,
~407 order items). There is no external dataset here — the schema and
question set were designed for this assignment so the "correct answer" is
unambiguous and independently re-derivable from a clean clone.

## How correctness was checked

1. Every `(question, gold_sql)` pair lives in `data/make_items.py`, not
   directly in the JSONL file.
2. Running `python data/make_items.py` executes every `gold_sql` against
   the freshly built `db/store.db` **before** writing `items.jsonl`. A
   query that raises a SQL error aborts the whole generation step — no
   item can reach the dataset with a typo or a bad join.
3. Each item's row count is printed at generation time (see the run log
   in this repo's history / CI). Two items legitimately return 0 rows:
   - "customers who have never placed an order" — every one of the 30
     customers ended up with at least one order in this random seed.
   - "products that have never appeared in any order" — same story for
     all 40 products.
   Both are kept intentionally: a model that hallucinates a non-empty
   answer here is a genuine wrong answer, not scoring noise.
4. A second person (or a second pass by the same author, re-reading each
   English question against its SQL cold, without looking at the first
   pass's intent) re-checked all 50 pairs for question/SQL mismatches —
   e.g. that "top 5" queries have `LIMIT 5`, that "rounded to 2 decimals"
   queries actually call `ROUND(...)`, and that every `ORDER BY` matches
   what the English question asks for.

## Difficulty split

| Difficulty | Count | Definition |
|---|---|---|
| easy | 15 | Single table, filter / order / limit / simple aggregate, no join |
| medium | 19 | Exactly one join, or a single-table `GROUP BY` |
| hard | 16 | Two or more joins, a subquery / CTE, or `HAVING` on a multi-join aggregate |

## Dev / test split

For Project 0 there is no train/test split — all 50 items are the test
set, run once per model per the brief ("the same 50 items, in the same
order" for all three models). If this task is extended into a larger
BIRD-style evaluation later (see the internship's Text2SQL agent), a
held-out dev slice should be carved out before adding more items.
