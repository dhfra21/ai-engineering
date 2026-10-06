# Inter-annotator agreement (claude-a vs claude-b)

- Items: 161 · labelled by both: 161 · by one only: 0 · by neither: 0
- Drop proposed by both: 0 · by one: 0
- **Raw agreement on good/bad: 157/161 (97.5%)** (95% CI [93.8, 99.0]%)
- **Cohen's kappa: 0.947** (almost perfect)
- Both said bad and named the same failed criteria: 53/58 (91.4%)

| claude-a ↓ / claude-b → | good | bad |
|---|---|---|
| good | 99 | 2 |
| bad | 2 | 58 |

| Slice | Agreement | Kappa |
|---|---|---|
| split=dev | 58/60 (96.7%) | 0.93 |
| split=test | 99/101 (98.0%) | 0.957 |
| difficulty=easy | 44/45 (97.8%) | 0.949 |
| difficulty=hard | 55/57 (96.5%) | 0.923 |
| difficulty=medium | 58/59 (98.3%) | 0.965 |
| source=baseline | 71/73 (97.3%) | 0.842 |
| source=perturbed | 55/56 (98.2%) | 0.879 |
| source=weak | 31/32 (96.9%) | 0.652 |

## Golden set: 161 items
- Labels: {'good': 85, 'bad': 76} · split: {'dev': 60, 'test': 101} · resolved by adjudication: 4
- Overridden after agreement: 14
  - c-q102 -> bad: Both labellers said good, but the explanation never mentions the ORDER BY times_ordered DESC; rule 3.3 requires the sort order and direction. Planted missing_condition error. claude-b's note ('most first') describes text that is not there. [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q017 -> bad: Rule 3.12 (guide v3): says 'every product category in the database', but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q020 -> bad: Rule 3.12 (guide v3): says 'every customer's name', but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q046 -> bad: Rule 3.12 (guide v3): says 'lists each product category' (categories with no sales are dropped), but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q088 -> bad: Rule 3.12 (guide v3): says 'lists each product category name' (categories with no order lines are dropped), but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q097 -> bad: Rule 3.12 (guide v3): says 'lists each product category', but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q098 -> bad: Rule 3.12 (guide v3): says 'lists each product category name', but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q099 -> bad: Rule 3.12 (guide v3): says 'lists each product category', but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q103 -> bad: Rule 3.12 (guide v3): says 'lists every product' (unsold products are dropped), but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q111 -> bad: Rule 3.12 (guide v3): says 'every customer's name', but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q138 -> bad: Rule 3.12 (guide v3): says 'the biggest purchase made by every customer', but the inner join drops those with no matching rows, so the stated row set is wrong. Found by a rule sweep over all 161 items, triggered by judge v1 dev disagreements (c-q020, c-q097, c-q111). [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q128 -> bad: Says the result is 'a list of customer names' and never mentions the total-spend column the query also returns (§2 completeness test: same columns). Found via a judge v1 dev disagreement; not swept for, so other column omissions may remain. [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q108 -> bad: Rule 3.12: says 'lists every order that is still pending', but the inner join drops orders with no match. Missed by the first rule-3.12 sweep (kept as good because orders without items don't occur in this data, which is judging by data, not SQL); surfaced by judge v2 on dev. [Corrected by Claude (orchestrating session), at the team's request.]
  - c-q095 -> bad: Rule 3.12: says 'lists every order in the database', but the inner join drops orders with no match. Missed by the first rule-3.12 sweep for the same reason; found while fixing c-q108, not by the judge. [Corrected by Claude (orchestrating session), at the team's request.]
- Pending adjudication: 0
- Dropped: 0
