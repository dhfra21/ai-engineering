# Judge reliability — judge/v2 on gptoss120b, dev split

- Items: 60 · judge call errors: 0 (excluded below)
- **Agreement with humans: 53/60 (88.3%)** (95% CI [77.8, 94.2]%) · **Cohen's kappa 0.765** (substantial)
- Human-bad answers the judge also calls bad (recall): 29/33 (87.9%)
- Judge-bad answers humans agree are bad (precision): 29/32 (90.6%)
- Cost per judged item (list price): $0.00050703 · latency p50 1752.5 ms, p95 4263.4 ms

| human ↓ / judge → | good | bad |
|---|---|---|
| good | 24 | 3 |
| bad | 4 | 29 |

| Slice | Agreement | Human-bad caught |
|---|---|---|
| difficulty=easy | 17/17 (100.0%) | 4/4 (100.0%) |
| difficulty=hard | 17/21 (81.0%) | 13/15 (86.7%) |
| difficulty=medium | 19/22 (86.4%) | 12/14 (85.7%) |
| source=baseline | 28/32 (87.5%) | 10/12 (83.3%) |
| source=perturbed | 17/18 (94.4%) | 17/18 (94.4%) |
| source=weak | 8/10 (80.0%) | 2/3 (66.7%) |
| error_type=invented_detail | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=jargon | 2/3 (66.7%) | 2/3 (66.7%) |
| error_type=missing_condition | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=wrong_aggregation | 3/3 (100.0%) | 3/3 (100.0%) |
| error_type=wrong_filter | 5/5 (100.0%) | 5/5 (100.0%) |
| error_type=wrong_join_semantics | 3/3 (100.0%) | 3/3 (100.0%) |

## Disagreements

- **c-q083** (weak) human=good judge=bad: The explanation omits that customers with multiple completed orders will appear once for each order, so it does not fully describe all rows the query returns.
- **c-q095** (baseline) human=bad judge=good: The explanation accurately describes all selected columns, the join relationship, and the ascending date order without adding any incorrect or extra details, and it is clear for a non‑SQL audience.
- **c-q099** (baseline) human=bad judge=good: The explanation accurately describes the query’s behavior, mentions all relevant operations (join, grouping, max price), does not add any unsupported claims, and is written in clear plain language.
- **c-q126** (baseline) human=good judge=bad: The explanation omits that the query orders the rows by month (ascending) for the change calculation, so it does not mention all ordering details required for completeness.
- **c-q127** (baseline) human=good judge=bad: The explanation says the query shows each product’s share of its category revenue for every product, but the query only includes products that have order items (inner join), so it misstates which rows are returned and omits that filter. This makes it both incorrect and incomplete.
- **c-q134** (weak) human=bad judge=good: The explanation accurately describes the query’s behavior, mentions the grouping by country and category, the revenue sum, the HAVING filter >200, and the descending order, without adding any incorrect or invented details, and is clear for a non‑SQL audience.
- **c-q140** (perturbed/jargon) human=bad judge=good: The explanation accurately describes every part of the query, mentions all filters, grouping, aggregation, and ordering, adds no unsupported details, and is written in plain language suitable for a non‑SQL audience.
