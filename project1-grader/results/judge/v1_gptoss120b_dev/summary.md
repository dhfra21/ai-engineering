# Judge reliability — judge/v1 on gptoss120b, dev split

- Items: 60 · judge call errors: 0 (excluded below)
- **Agreement with humans: 53/60 (88.3%)** (95% CI [77.8, 94.2]%) · **Cohen's kappa 0.768** (substantial)
- Human-bad answers the judge also calls bad (recall): 27/33 (81.8%)
- Judge-bad answers humans agree are bad (precision): 27/28 (96.4%)
- Cost per judged item (list price): $0.00046029 · latency p50 1515.7 ms, p95 2918.2 ms

| human ↓ / judge → | good | bad |
|---|---|---|
| good | 26 | 1 |
| bad | 6 | 27 |

| Slice | Agreement | Human-bad caught |
|---|---|---|
| difficulty=easy | 17/17 (100.0%) | 4/4 (100.0%) |
| difficulty=hard | 19/21 (90.5%) | 13/15 (86.7%) |
| difficulty=medium | 17/22 (77.3%) | 10/14 (71.4%) |
| source=baseline | 27/32 (84.4%) | 7/12 (58.3%) |
| source=perturbed | 17/18 (94.4%) | 17/18 (94.4%) |
| source=weak | 9/10 (90.0%) | 3/3 (100.0%) |
| error_type=invented_detail | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=jargon | 2/3 (66.7%) | 2/3 (66.7%) |
| error_type=missing_condition | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=wrong_aggregation | 3/3 (100.0%) | 3/3 (100.0%) |
| error_type=wrong_filter | 5/5 (100.0%) | 5/5 (100.0%) |
| error_type=wrong_join_semantics | 3/3 (100.0%) | 3/3 (100.0%) |

## Disagreements

- **c-q046** (baseline) human=bad judge=good: The explanation accurately describes the query’s behavior, includes all relevant aspects (category grouping, distinct customer count, sorting), adds no unsupported details, and is clear for a non‑SQL audience.
- **c-q083** (weak) human=good judge=bad: The explanation omits that customers with multiple completed orders will appear once for each order, which affects the number of rows returned.
- **c-q095** (baseline) human=bad judge=good: The explanation accurately describes all selected columns, the join to get the customer's country, includes all orders, and correctly notes the ascending date order. It mentions no extra details and is clear for a non‑SQL audience.
- **c-q098** (baseline) human=bad judge=good: The explanation accurately describes the query’s behavior, includes all relevant operations (grouping, counting, total count, percentage calculation, rounding), does not add any unsupported details, and is written in plain language understandable to a non‑SQL audience.
- **c-q099** (baseline) human=bad judge=good: The explanation accurately describes the query’s behavior, mentions all relevant operations (join, grouping, max aggregation), adds no unsupported details, and is written in clear plain language.
- **c-q108** (baseline) human=bad judge=good: The explanation accurately describes the pending orders filter, the total cost calculation per order, and the descending sort, without adding any incorrect or extra details, and is clear for a non‑SQL audience.
- **c-q140** (perturbed/jargon) human=bad judge=good: The explanation accurately describes every part of the query, mentions all filters, grouping, aggregation, and ordering, adds no extra information, and is expressed in plain language suitable for a non‑SQL audience.
