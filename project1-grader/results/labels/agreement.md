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
- Labels: {'good': 98, 'bad': 63} · split: {'dev': 60, 'test': 101} · resolved by adjudication: 4
- Overridden after agreement: 1
  - c-q102 -> bad: Both labellers said good, but the explanation never mentions the ORDER BY times_ordered DESC; rule 3.3 requires the sort order and direction. Planted missing_condition error. claude-b's note ('most first') describes text that is not there. [Corrected by Claude (orchestrating session), at the team's request.]
- Pending adjudication: 0
- Dropped: 0
