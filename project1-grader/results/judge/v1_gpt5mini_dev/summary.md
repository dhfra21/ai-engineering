# Judge reliability — judge/v1 on gpt5mini, dev split

- Items: 60 · judge call errors: 0 (excluded below)
- **Agreement with humans: 54/60 (90.0%)** (95% CI [79.9, 95.3]%) · **Cohen's kappa 0.789** (substantial)
- Human-bad answers the judge also calls bad (recall): 34/36 (94.4%)
- Judge-bad answers humans agree are bad (precision): 34/38 (89.5%)
- Cost per judged item (list price): $0.00200855 · latency p50 8452.9 ms, p95 17564.2 ms

| human ↓ / judge → | good | bad |
|---|---|---|
| good | 20 | 4 |
| bad | 2 | 34 |

| Slice | Agreement | Human-bad caught |
|---|---|---|
| difficulty=easy | 16/17 (94.1%) | 4/4 (100.0%) |
| difficulty=hard | 18/21 (85.7%) | 16/17 (94.1%) |
| difficulty=medium | 20/22 (90.9%) | 14/15 (93.3%) |
| source=baseline | 29/32 (90.6%) | 13/14 (92.9%) |
| source=perturbed | 17/18 (94.4%) | 17/18 (94.4%) |
| source=weak | 8/10 (80.0%) | 4/4 (100.0%) |
| error_type=invented_detail | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=jargon | 2/3 (66.7%) | 2/3 (66.7%) |
| error_type=missing_condition | 2/2 (100.0%) | 2/2 (100.0%) |
| error_type=wrong_aggregation | 3/3 (100.0%) | 3/3 (100.0%) |
| error_type=wrong_filter | 5/5 (100.0%) | 5/5 (100.0%) |
| error_type=wrong_join_semantics | 3/3 (100.0%) | 3/3 (100.0%) |

## Disagreements

- **c-q014** (weak) human=good judge=bad: The explanation is correct and clear about the table, grouping and count, but it’s incomplete because it doesn’t state the ORDER BY direction. The query orders years in ascending order (ORDER BY year), and the explanation only says “sorted by year” without specifying that.
- **c-q083** (weak) human=good judge=bad: The explanation misses an important detail: customers with more than one completed order will appear multiple times (one row per completed order). It also uses “blank” instead of stating the order_id is NULL for customers without completed orders, but the main omission is the multiplicity of rows per customer.
- **c-q107** (baseline) human=bad judge=good: The explanation correctly and completely describes that the query returns one column containing every city value from customers followed by every country value, and explicitly notes that duplicates are not removed (UNION ALL). It makes no claims beyond what the SQL does and is expressed in clear, non‑SQL language.
- **c-q126** (baseline) human=good judge=bad: The explanation is accurate and clear about the main result, but it omits some details that affect the returned rows and values: it doesn’t say that the revenue comes from the joined order_items (so completed orders with no items won’t appear), it doesn’t mention that the month is created by taking the first 7 characters of order_date (YYYY-MM), and it doesn’t state that the month-over-month difference uses the previous row as determined by ordering months (i.e. LAG over months) nor that the first month’s change will be NULL. Those omissions affect which rows/values appear, so the explanation is incomplete.
- **c-q127** (baseline) human=good judge=bad: The explanation says it computes totals “for every product” and describes revenue as “price times quantity sold,” but the query sums order_items.unit_price * quantity and uses an inner join between products and order_items — so products with no order_items (no sales) are excluded. The explanation fails to mention this exclusion (and thus overstates coverage), so it is incomplete and makes a claim the query does not support. The parts about dividing by the category total and rounding to one decimal are correct and clear.
- **c-q140** (perturbed/jargon) human=bad judge=good: The explanation correctly and completely states the selected columns, the inner join on customer_id, the COUNT(DISTINCT substr(...)) counting distinct year-month buckets, the GROUP BY by customer, the HAVING filter for at least six active months, and the ORDER BY active_months DESC; it uses plain-language phrasing that a non-SQL reader can follow. No behavior or filter is invented or misstated.
