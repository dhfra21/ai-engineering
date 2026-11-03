# Judge reliability — judge/v2 on gpt5mini, dev split

- Items: 60 · judge call errors: 0 (excluded below)
- **Agreement with humans: 54/60 (90.0%)** (95% CI [79.9, 95.3]%) · **Cohen's kappa 0.783** (substantial)
- Human-bad answers the judge also calls bad (recall): 36/36 (100.0%)
- Judge-bad answers humans agree are bad (precision): 36/42 (85.7%)
- Cost per judged item (list price): $0.00217708 · latency p50 8727.8 ms, p95 19032.2 ms

| human ↓ / judge → | good | bad |
|---|---|---|
| good | 18 | 6 |
| bad | 0 | 36 |

| Slice | Agreement | Human-bad caught |
|---|---|---|
| difficulty=easy | 16/17 (94.1%) | 4/4 (100.0%) |
| difficulty=hard | 20/21 (95.2%) | 17/17 (100.0%) |
| difficulty=medium | 18/22 (81.8%) | 15/15 (100.0%) |
| source=baseline | 28/32 (87.5%) | 14/14 (100.0%) |
| source=perturbed | 18/18 (100.0%) | 18/18 (100.0%) |
| source=weak | 8/10 (80.0%) | 4/4 (100.0%) |
| error_type=invented_detail | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=jargon | 3/3 (100.0%) | 3/3 (100.0%) |
| error_type=missing_condition | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=wrong_aggregation | 3/3 (100.0%) | 3/3 (100.0%) |
| error_type=wrong_filter | 5/5 (100.0%) | 5/5 (100.0%) |
| error_type=wrong_join_semantics | 3/3 (100.0%) | 3/3 (100.0%) |

## Disagreements

- **c-q014** (weak) human=good judge=bad: The explanation is accurate and clear but omits the ORDER BY direction. The query orders the results by year in ascending order; the explanation only says "sorted by year" without specifying the direction.
- **c-q030** (baseline) human=good judge=bad: The explanation implies it lists counts for “each month in the year 2024,” which suggests all 12 months will appear; the query only returns months present in the orders table within that date range (months with zero orders are omitted). Otherwise the description correctly states the YYYY‑MM format, counting orders per month for 2024 and ordering by month.
- **c-q083** (weak) human=good judge=bad: The explanation omits an important row-level detail: a customer with multiple completed orders will appear once for each completed order (multiple rows), and it doesn't state that the missing order ID will be NULL (the query returns NULL, not a non-SQL-specific “blank”). Because it fails to mention how multiple orders affect the returned rows, it is incomplete.
- **c-q106** (baseline) human=good judge=bad: The explanation correctly says the query returns names from both tables and that UNION removes duplicates, and it is clear. However it is incomplete because it doesn't state anything about ordering: the query has no ORDER BY, so the row order is not guaranteed. A reader reproducing the result would not know the (unspecified) order.
- **c-q112** (baseline) human=good judge=bad: The explanation implies it reports counts “on each day of the week” (i.e., all seven days). The query groups only the weekdays that actually appear in the orders table, so days with zero orders will not be shown. Otherwise the description of how weekdays are encoded, that it counts orders per weekday, and that results are ordered Sunday-to-Saturday is correct and clear.
- **c-q127** (baseline) human=good judge=bad: The explanation omits an important filter: the query only uses products that have matching order_items (products with sales), because it INNER JOINs products to order_items and groups on those rows. Saying “for each product” and “sum of revenue for all products in the same category” implies it covers unsold products too; the category total and percentages are computed only from products that have revenue. Because it leaves out that exclusion, it is not correct or complete.
