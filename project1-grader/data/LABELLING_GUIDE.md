# Labelling guide: SQL explanations

**Version 1.** If you change a rule, bump the version and add a line under
"Changes" at the bottom. Then check that `prompts/judge/*.md` still says the
same thing, because the judge is graded against labels made with this guide.

## 1. The task

The system reads a SQLite query and explains in plain words what it returns.
The reader is a **business analyst who does not know SQL** and will make
decisions from the explanation.

You get one explanation per item, and you label it **good** or **bad**.

On screen you also see:
- the SQL itself, which is the ground truth
- the first rows of the query's real result
- the query author's note (what the query was meant to compute)
- sometimes a "known trap" note

The author's note and the trap note are only references. If one of them
disagrees with the SQL, the SQL wins. Report the conflict with **d**
(see §4).

## 2. An explanation is GOOD only if it passes all four criteria

| # | Criterion | Fails when… |
|---|---|---|
| 1 | **correct** | Any statement about what the query does is false, or clearly implies the wrong behaviour. This covers the rows used, filters, how joins keep or drop rows, grouping, the kind of aggregate (count / sum / average; rows vs distinct values; units vs order lines), sort direction, limit, and what each output column means. |
| 2 | **complete** | It leaves out something that changes which rows, values or order the reader gets: a filter, the grouping, an aggregate, `DISTINCT`, `LIMIT`/`OFFSET`, or the `ORDER BY` with its direction. |
| 3 | **no_invention** | It claims something the query does not support: an extra filter, a time period, a business meaning ("loyal customers", "this year"), or specific result values. |
| 4 | **clear** | A non-SQL reader could not follow it. That includes unexplained jargon (JOIN, GROUP BY, NULL, subquery, window function, CTE), a clause-by-clause English copy of the SQL, or a main point buried so deep you have to hunt for it. |

**The completeness test:** could the reader build the same table from your
explanation alone, with the same rows, the same columns (in meaning, not
name) and the same order? If not, something is missing.

When you choose **bad**, tick every criterion that fails.

## 3. Decision rules (the cases we argued about)

1. **Silence is fine; being wrong is not.** You don't have to mention an
   edge case such as ties, NULLs, customers with no orders, or cancelled
   orders being included. If the explanation states or clearly implies the
   wrong behaviour, that's a **correct** failure. Example: "each customer
   and their number of orders" says nothing about customers with zero
   orders, and that's fine. "Customers with no orders show 0" when the
   query shows 1 is **bad**.
2. **Things you don't need to mention:** column aliases, the exact rounding
   precision (but "rounded" vs "exact" matters if it's stated wrongly),
   `AS` names, index use, SQL execution order, and the table prefixes
   `p.`/`c.`.
3. **Things you must mention:** every filter condition, the value being
   aggregated and how it's aggregated, the grouping level, `DISTINCT` when
   it changes the result, the `LIMIT` number, and the sort order with its
   direction. If there's **no** `ORDER BY`, the explanation must not promise
   an order.
4. **Plain words beat column names**, but naming a column is fine
   ("the `unit_price`, the price paid at the time of the order"). Leaving a
   single term such as "join" unexplained is only a **clear** failure if it
   would actually confuse the reader.
5. **Length is not quality.** A two-sentence explanation that passes all
   four criteria is good. Friendly framing, restating the same point, or
   generic SQL background neither help nor hurt. They only hurt when the
   main point gets hard to find (**clear**).
6. **"Top N" wording must match the query.** "The most expensive products"
   is incomplete for `LIMIT 5`, because the reader needs to know it's 5.
   "The most expensive product" (singular) for `LIMIT 1` is fine.
7. **Numbers written out must be right.** "More than 5" vs "5 or more" is a
   **correct** failure when it's wrong. Dates must match the query's date
   range.
8. **Minor wording slips that wouldn't mislead are fine.** Label what an
   attentive reader would come away believing.
9. **Unsure?** Re-read §2, pick the label you'd defend, and write a note.
   Don't use **d** to dodge a hard call.

## 4. How we label

- **Independently.** Each labeller uses their own file
  (`python -m harness.label --labeller <name>`). Don't discuss items, don't
  open the other person's file, and don't open `data/candidates.jsonl` (it
  shows where each answer came from) until you've both finished.
- **Calibrate first, on the examples in §6, not on dataset items.** Label
  them on your own, compare, and settle any disagreement by re-reading this
  guide. That way the agreement we report on the dataset stays independent.
- **Budget:** about 1 minute per item, so roughly 3 hours per person for
  161 items. Split it into sessions of 40–50 items, because fatigue lowers
  agreement.
- **d = propose dropping** is only for items that are broken as data: the
  SQL is ambiguous, the author's note contradicts the SQL, or the
  explanation is empty or garbled beyond grading. Give a reason every time.
- **Adjudication.** `python -m harness.golden --a <you> --b <them>` reports
  raw agreement and writes the disagreements to
  `data/labels/adjudication.jsonl`. Discuss each one with this guide open,
  then fill in `final`, `final_failed_criteria` and `reason`. If you
  disagreed because a rule was unclear, fix the rule here (§7) and mention
  it in the postmortem. Don't re-label items you agreed on.

## 5. Dev/test split (and how not to cheat)

- `data/make_queries.py` fixes the split with seed 496, stratified by
  difficulty: **60 dev / 101 test**. It never changes.
- **Prompt changes (system or judge) are tuned on dev only.**
- Run **test** once per version you intend to report, and never use it to
  choose between versions.
- The golden set follows the same split. Judge agreement is developed on
  golden-dev and **reported on golden-test**.

## 6. Worked examples

Use these for calibration. Some of the queries also appear in the dataset,
but these explanations don't, so calibrating on them doesn't leak any
dataset labels.

**A.** `SELECT c.name FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_id IS NULL ORDER BY c.name;`
- ✅ *"The names of customers who have never placed an order, sorted
  alphabetically."*
- ❌ correct: *"Lists customers and their orders, keeping only orders
  whose ID is missing."* This misreads the LEFT JOIN/IS NULL pattern.
- ❌ clear: *"Performs a LEFT JOIN from customers to orders on
  customer_id, filters rows where o.order_id IS NULL, projects c.name
  ordered ascending."* Every fact is right, but it's SQL written in
  English.

**B.** `SELECT c.name, COUNT(*) AS n FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id;`
- ✅ *"Each customer's name with a count of their orders. Because of how
  the count is written, a customer with no orders would show 1, not 0.
  No particular order."*
- ✅ *"Each customer with the number of orders they have placed."* This is
  silent on the zero-orders edge case, which is allowed (rule 3.1).
- ❌ correct: *"Each customer with their number of orders; customers who
  never ordered show 0."*

**C.** `SELECT name, price FROM products ORDER BY price DESC LIMIT 5;`
- ✅ *"The five most expensive products and their prices, from most to
  least expensive."*
- ❌ complete: *"The most expensive products and their prices."* The
  reader can't tell it's five.
- ❌ no_invention: *"The five most expensive products currently in stock,
  …"* The query has no stock filter.

**D.** `SELECT ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 1) FROM orders;`
- ✅ *"The percentage of all orders that are completed, rounded to one
  decimal place."*
- ✅ *"What share of all orders have been completed, as a percentage."*
  It leaves out the rounding precision, which is allowed (rule 3.2).
- ❌ correct: *"The percentage of non-cancelled orders that are
  completed."* That's the wrong denominator.

**E.** `SELECT country, COUNT(*) FROM customers GROUP BY country HAVING COUNT(*) >= 3;`
- ❌ correct: *"Countries with more than 3 customers, and how many
  customers each has."* The query means 3 or more (rule 3.7).
- ❌ clear, but not because it's long: a 200-word answer whose first
  paragraph is a general introduction to SQL, with the actual meaning
  buried in paragraph three.

## 7. Changes

- v1: first version.
