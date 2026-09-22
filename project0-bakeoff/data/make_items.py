"""Generate + verify data/items.jsonl against db/store.db.

Every gold_sql is executed here before it is written out, so a bad label
(typo, wrong join, empty result by accident) fails loudly at generation
time instead of silently corrupting the eval later. Run:

    python db/build_db.py
    python data/make_items.py
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "store.db"
OUT_PATH = Path(__file__).parent / "items.jsonl"

# (difficulty, question, gold_sql)
ITEMS: list[tuple[str, str, str]] = [
    # ---- easy: single table, no join ----
    ("easy", "List the names of all customers from Tunisia, ordered alphabetically by name.",
     "SELECT name FROM customers WHERE country = 'Tunisia' ORDER BY name;"),
    ("easy", "What is the price of the product named 'Dune'?",
     "SELECT price FROM products WHERE name = 'Dune';"),
    ("easy", "List all product names that are currently out of stock, ordered by name.",
     "SELECT name FROM products WHERE in_stock = 0 ORDER BY name;"),
    ("easy", "List the 5 most expensive products with their prices, from most to least expensive.",
     "SELECT name, price FROM products ORDER BY price DESC LIMIT 5;"),
    ("easy", "List all order IDs with status 'cancelled', ordered by order ID.",
     "SELECT order_id FROM orders WHERE status = 'cancelled' ORDER BY order_id;"),
    ("easy", "What are the names of all categories, in alphabetical order?",
     "SELECT name FROM categories ORDER BY name;"),
    ("easy", "List the names of customers who signed up in 2023, ordered by signup date.",
     "SELECT name FROM customers WHERE signup_date BETWEEN '2023-01-01' AND '2023-12-31' ORDER BY signup_date;"),
    ("easy", "List all order IDs placed in March 2024, ordered by order date.",
     "SELECT order_id FROM orders WHERE order_date BETWEEN '2024-03-01' AND '2024-03-31' ORDER BY order_date;"),
    ("easy", "How many products are currently in stock?",
     "SELECT COUNT(*) FROM products WHERE in_stock = 1;"),
    ("easy", "List the names of customers based in London, ordered by name.",
     "SELECT name FROM customers WHERE city = 'London' ORDER BY name;"),
    ("easy", "What is the average price of all products, rounded to 2 decimal places?",
     "SELECT ROUND(AVG(price), 2) FROM products;"),
    ("easy", "How many orders have status 'pending'?",
     "SELECT COUNT(*) FROM orders WHERE status = 'pending';"),
    ("easy", "What is the name of the most expensive product that is currently out of stock?",
     "SELECT name FROM products WHERE in_stock = 0 ORDER BY price DESC LIMIT 1;"),
    ("easy", "How many customers signed up in each year? Show year and count, ordered by year.",
     "SELECT substr(signup_date, 1, 4) AS year, COUNT(*) AS n FROM customers GROUP BY year ORDER BY year;"),
    ("easy", "What percentage of orders have status 'completed'? Round to 1 decimal place.",
     "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 1) FROM orders;"),

    # ---- medium: exactly one join, or single-table GROUP BY already counted above ----
    ("medium", "List all product names in the 'Electronics' category, ordered by price descending.",
     "SELECT p.name FROM products p JOIN categories c ON p.category_id = c.category_id "
     "WHERE c.name = 'Electronics' ORDER BY p.price DESC;"),
    ("medium", "How many products are there in each category? Show category name and count, ordered by category name.",
     "SELECT c.name AS category, COUNT(*) AS n FROM products p JOIN categories c ON p.category_id = c.category_id "
     "GROUP BY c.name ORDER BY c.name;"),
    ("medium", "What is the average price of products in each category? Show category name and average price "
     "rounded to 2 decimals, ordered by average price descending.",
     "SELECT c.name AS category, ROUND(AVG(p.price), 2) AS avg_price FROM products p "
     "JOIN categories c ON p.category_id = c.category_id GROUP BY c.name ORDER BY avg_price DESC;"),
    ("medium", "List the names of customers who have never placed an order, ordered by name.",
     "SELECT c.name FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id "
     "WHERE o.order_id IS NULL ORDER BY c.name;"),
    ("medium", "How many orders has each customer placed? Show customer name and order count, ordered by "
     "order count descending, then by name.",
     "SELECT c.name, COUNT(o.order_id) AS n_orders FROM customers c JOIN orders o "
     "ON c.customer_id = o.customer_id GROUP BY c.name ORDER BY n_orders DESC, c.name;"),
    ("medium", "List the names of products in the 'Books' category that cost less than 20, ordered by name.",
     "SELECT p.name FROM products p JOIN categories c ON p.category_id = c.category_id "
     "WHERE c.name = 'Books' AND p.price < 20 ORDER BY p.name;"),
    ("medium", "What is the total quantity of 'Yoga Mat' units sold across all orders?",
     "SELECT SUM(oi.quantity) FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
     "WHERE p.name = 'Yoga Mat';"),
    ("medium", "How many orders are there for each status? Show status and count, ordered by status name.",
     "SELECT status, COUNT(*) AS n FROM orders GROUP BY status ORDER BY status;"),
    ("medium", "What is the total revenue (quantity times unit price) from all order items, rounded to 2 decimals?",
     "SELECT ROUND(SUM(quantity * unit_price), 2) FROM order_items;"),
    ("medium", "List the names of customers from 'France' who signed up before 2023-06-01, ordered by name.",
     "SELECT name FROM customers WHERE country = 'France' AND signup_date < '2023-06-01' ORDER BY name;"),
    ("medium", "List the 5 products with the highest total quantity sold, showing product name and total quantity.",
     "SELECT p.name, SUM(oi.quantity) AS total_qty FROM order_items oi JOIN products p "
     "ON oi.product_id = p.product_id GROUP BY p.name ORDER BY total_qty DESC LIMIT 5;"),
    ("medium", "List the distinct names of customers who placed at least one 'cancelled' order, ordered by name.",
     "SELECT DISTINCT c.name FROM customers c JOIN orders o ON c.customer_id = o.customer_id "
     "WHERE o.status = 'cancelled' ORDER BY c.name;"),
    ("medium", "List the names of products that have never appeared in any order, ordered by name.",
     "SELECT p.name FROM products p LEFT JOIN order_items oi ON p.product_id = oi.product_id "
     "WHERE oi.order_item_id IS NULL ORDER BY p.name;"),
    ("medium", "List the top 3 customers by number of orders placed, showing name and order count.",
     "SELECT c.name, COUNT(*) AS n FROM customers c JOIN orders o ON c.customer_id = o.customer_id "
     "GROUP BY c.name ORDER BY n DESC LIMIT 3;"),
    ("medium", "How many orders were placed in each month of 2024? Show month as YYYY-MM and count, "
     "ordered by month.",
     "SELECT substr(order_date, 1, 7) AS month, COUNT(*) AS n FROM orders "
     "WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY month ORDER BY month;"),
    ("medium", "List the names of customers and the date of their most recent order, for customers who have "
     "placed at least one order, ordered by most recent order date descending.",
     "SELECT c.name, MAX(o.order_date) AS last_order FROM customers c JOIN orders o "
     "ON c.customer_id = o.customer_id GROUP BY c.name ORDER BY last_order DESC;"),
    ("medium", "List the names of categories that have more than 5 products, with the product count, "
     "ordered by count descending.",
     "SELECT c.name, COUNT(*) AS n FROM products p JOIN categories c ON p.category_id = c.category_id "
     "GROUP BY c.name HAVING COUNT(*) > 5 ORDER BY n DESC;"),
    ("medium", "List the names of products that cost more than the average product price, ordered by name.",
     "SELECT name FROM products WHERE price > (SELECT AVG(price) FROM products) ORDER BY name;"),
    ("medium", "List the names of products priced within 10% of the most expensive product in the store, "
     "ordered by price descending.",
     "SELECT name FROM products WHERE price >= 0.9 * (SELECT MAX(price) FROM products) ORDER BY price DESC;"),

    # ---- hard: 2+ joins, subqueries/CTEs, or HAVING on a multi-join aggregate ----
    ("hard", "How many distinct products has the customer 'James Smith' ordered?",
     "SELECT COUNT(DISTINCT oi.product_id) FROM order_items oi "
     "JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id "
     "WHERE c.name = 'James Smith';"),
    ("hard", "List the top 5 customers by total revenue (quantity times unit price) from completed orders, "
     "showing name and revenue rounded to 2 decimals.",
     "SELECT c.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue FROM customers c "
     "JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id "
     "WHERE o.status = 'completed' GROUP BY c.name ORDER BY revenue DESC LIMIT 5;"),
    ("hard", "List the distinct names of customers who have ordered the product 'Ergonomic Chair', "
     "ordered by name.",
     "SELECT DISTINCT c.name FROM customers c JOIN orders o ON c.customer_id = o.customer_id "
     "JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id "
     "WHERE p.name = 'Ergonomic Chair' ORDER BY c.name;"),
    ("hard", "List the names of customers who have placed 5 or more orders, with their order count, "
     "ordered by order count descending then name.",
     "SELECT c.name, COUNT(*) AS n FROM customers c JOIN orders o ON c.customer_id = o.customer_id "
     "GROUP BY c.name HAVING COUNT(*) >= 5 ORDER BY n DESC, c.name;"),
    ("hard", "List the names of categories that have no products priced above 100, ordered by name.",
     "SELECT name FROM categories cat WHERE NOT EXISTS "
     "(SELECT 1 FROM products p WHERE p.category_id = cat.category_id AND p.price > 100) ORDER BY name;"),
    ("hard", "For each category, what is the name and price of its most expensive product? "
     "Show category name, product name, and price, ordered by category name.",
     "SELECT c.name AS category, p.name AS product, p.price FROM products p "
     "JOIN categories c ON p.category_id = c.category_id "
     "WHERE p.price = (SELECT MAX(p2.price) FROM products p2 WHERE p2.category_id = p.category_id) "
     "ORDER BY c.name;"),
    ("hard", "What is the total revenue (quantity times unit price) from completed orders only, "
     "rounded to 2 decimals?",
     "SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) FROM order_items oi "
     "JOIN orders o ON oi.order_id = o.order_id WHERE o.status = 'completed';"),
    ("hard", "Which 3 countries generated the most total revenue from completed orders? Show country and "
     "revenue rounded to 2 decimals, ordered by revenue descending.",
     "SELECT c.country, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue FROM customers c "
     "JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id "
     "WHERE o.status = 'completed' GROUP BY c.country ORDER BY revenue DESC LIMIT 3;"),
    ("hard", "List the names of customers whose number of orders is above the average number of orders "
     "per customer, counting only customers with at least one order, ordered by name.",
     "WITH counts AS (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id) "
     "SELECT c.name FROM customers c JOIN counts ct ON c.customer_id = ct.customer_id "
     "WHERE ct.n > (SELECT AVG(n) FROM counts) ORDER BY c.name;"),
    ("hard", "List the 5 products that generated the most total revenue (quantity times unit price), "
     "showing product name and revenue rounded to 2 decimals.",
     "SELECT p.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue FROM order_items oi "
     "JOIN products p ON oi.product_id = p.product_id GROUP BY p.name ORDER BY revenue DESC LIMIT 5;"),
    ("hard", "Which customers have spent more than 300 in total on completed orders? Show name and total "
     "spent rounded to 2 decimals, ordered by total spent descending.",
     "SELECT c.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_spent FROM customers c "
     "JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id "
     "WHERE o.status = 'completed' GROUP BY c.name HAVING total_spent > 300 ORDER BY total_spent DESC;"),
    ("hard", "For each category, how many distinct customers have bought at least one product from it? "
     "Show category name and customer count, ordered by customer count descending then category name.",
     "SELECT cat.name, COUNT(DISTINCT o.customer_id) AS n_customers FROM categories cat "
     "JOIN products p ON p.category_id = cat.category_id JOIN order_items oi ON oi.product_id = p.product_id "
     "JOIN orders o ON o.order_id = oi.order_id GROUP BY cat.name ORDER BY n_customers DESC, cat.name;"),
    ("hard", "List the names of customers who have ordered products from at least 3 different categories, "
     "with the category count, ordered by category count descending then name.",
     "SELECT c.name, COUNT(DISTINCT p.category_id) AS n_categories FROM customers c "
     "JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id "
     "JOIN products p ON oi.product_id = p.product_id GROUP BY c.name HAVING n_categories >= 3 "
     "ORDER BY n_categories DESC, c.name;"),
    ("hard", "What is the name of the product that generated the single highest revenue "
     "(quantity times unit price) from a single order item row?",
     "SELECT p.name FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
     "ORDER BY oi.quantity * oi.unit_price DESC LIMIT 1;"),
    ("hard", "List the names of customers who have never ordered a product from the 'Electronics' "
     "category, ordered by name.",
     "SELECT c.name FROM customers c WHERE c.customer_id NOT IN ("
     "SELECT o.customer_id FROM orders o JOIN order_items oi ON o.order_id = oi.order_id "
     "JOIN products p ON oi.product_id = p.product_id JOIN categories cat ON p.category_id = cat.category_id "
     "WHERE cat.name = 'Electronics') ORDER BY c.name;"),
    ("hard", "What is the average order value (sum of quantity times unit price per order), rounded to "
     "2 decimals, considering only completed orders?",
     "SELECT ROUND(AVG(order_total), 2) FROM (SELECT o.order_id, SUM(oi.quantity * oi.unit_price) AS order_total "
     "FROM orders o JOIN order_items oi ON o.order_id = oi.order_id WHERE o.status = 'completed' "
     "GROUP BY o.order_id);"),
]


def main() -> None:
    assert len(ITEMS) == 50, f"expected 50 items, got {len(ITEMS)}"

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA query_only = TRUE;")  # belt-and-braces: refuse any accidental write
    cur = conn.cursor()

    records = []
    errors = []
    for i, (difficulty, question, gold_sql) in enumerate(ITEMS, start=1):
        try:
            cur.execute(gold_sql)
            rows = cur.fetchall()
        except sqlite3.Error as e:
            errors.append(f"item {i}: {e}\n  SQL: {gold_sql}")
            continue
        records.append({
            "id": i,
            "difficulty": difficulty,
            "question": question,
            "gold_sql": gold_sql,
            "_row_count_check": len(rows),  # sanity only, not used by score.py
        })
        flag = " <-- EMPTY RESULT, double-check this is intentional" if len(rows) == 0 else ""
        print(f"{i:2d} [{difficulty:6s}] {len(rows):3d} rows{flag}  {question[:70]}")

    if errors:
        print("\n--- SQL ERRORS ---")
        for e in errors:
            print(e)
        raise SystemExit(f"\n{len(errors)} item(s) failed to execute — fix before writing items.jsonl")

    # Strip the internal sanity field before writing the real dataset file.
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for r in records:
            r = {k: v for k, v in r.items() if not k.startswith("_")}
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_diff: dict[str, int] = {}
    for _, d, _ in ITEMS:
        by_diff[d] = by_diff.get(d, 0) + 1
    print(f"\nWrote {len(records)} items to {OUT_PATH}")
    print("Difficulty mix:", by_diff)


if __name__ == "__main__":
    main()
