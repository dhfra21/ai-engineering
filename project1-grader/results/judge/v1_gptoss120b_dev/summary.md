# Judge reliability — judge/v1 on gptoss120b, dev split

- Items: 60 · judge call errors: 0 (excluded below)
- **Agreement with humans: 54/60 (90.0%)** (95% CI [79.9, 95.3]%) · **Cohen's kappa 0.797** (substantial)
- Human-bad answers the judge also calls bad (recall): 23/24 (95.8%)
- Judge-bad answers humans agree are bad (precision): 23/28 (82.1%)
- Cost per judged item (list price): $0.00046029 · latency p50 1515.7 ms, p95 2918.2 ms

| human ↓ / judge → | good | bad |
|---|---|---|
| good | 31 | 5 |
| bad | 1 | 23 |

| Slice | Agreement | Human-bad caught |
|---|---|---|
| difficulty=easy | 17/17 (100.0%) | 4/4 (100.0%) |
| difficulty=hard | 19/21 (90.5%) | 12/13 (92.3%) |
| difficulty=medium | 18/22 (81.8%) | 7/7 (100.0%) |
| source=baseline | 29/32 (90.6%) | 4/4 (100.0%) |
| source=perturbed | 17/18 (94.4%) | 17/18 (94.4%) |
| source=weak | 8/10 (80.0%) | 2/2 (100.0%) |
| error_type=invented_detail | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=jargon | 2/3 (66.7%) | 2/3 (66.7%) |
| error_type=missing_condition | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=wrong_aggregation | 3/3 (100.0%) | 3/3 (100.0%) |
| error_type=wrong_filter | 5/5 (100.0%) | 5/5 (100.0%) |
| error_type=wrong_join_semantics | 3/3 (100.0%) | 3/3 (100.0%) |

## Disagreements

- **c-q020** (baseline) human=good judge=bad: The explanation says the query lists every customer’s name and their order count, implying customers with zero orders are included and that each distinct customer is counted separately. In fact, the inner join excludes customers with no orders and grouping by name merges customers sharing the same name, so the description is incorrect, incomplete, and invents behavior not present.
- **c-q083** (weak) human=good judge=bad: The explanation omits that customers with multiple completed orders will appear once for each order, which affects the number of rows returned.
- **c-q097** (baseline) human=good judge=bad: The explanation says the query lists each product category, implying all categories are returned, but the inner join excludes categories with no products, so the statement about which rows are returned is incorrect and incomplete. It also omits that categories without products are omitted, a detail that affects the result set.
- **c-q111** (baseline) human=good judge=bad: The explanation says the query lists every customer’s name, but the inner join means only customers with at least one order are returned, so it misstates the result set and omits that customers without orders are excluded. This makes it both incorrect and incomplete.
- **c-q128** (weak) human=good judge=bad: The explanation leaves out that the query returns both the customer name and the total spend amount, mentioning only names, so it does not fully describe all output columns.
- **c-q140** (perturbed/jargon) human=bad judge=good: The explanation accurately describes every part of the query, mentions all filters, grouping, aggregation, and ordering, adds no extra information, and is expressed in plain language suitable for a non‑SQL audience.
