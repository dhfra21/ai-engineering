"""Build data/queries.jsonl — the 161 SQL queries the system has to explain.

Run:
    python db/build_db.py          # once
    python data/make_queries.py

Every query is executed against db/store.db before anything is written; a
query that errors aborts the whole step, so no broken SQL can reach the
dataset. The dev/test split is assigned here too (seeded, stratified by
difficulty) and never changes afterwards — see LABELLING_GUIDE.md §5.

Fields per query:
    id          "q001".."q161"
    difficulty  easy | medium | hard
    sql         the input the system explains
    intent      what the query author meant, in plain words. The labellers and
                the judge see it as a reference; the SYSTEM never sees it.
    watch_for   (optional) the specific trap a careless explanation falls into.
                Shown to labellers and the judge, never to the system.
    origin      "p0" (question/gold SQL reused from Project 0) or "p1" (new)
    split       dev | test
"""
from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "db" / "store.db"
OUT_PATH = ROOT / "data" / "queries.jsonl"
SPLIT_SEED = 496
DEV_FRACTION = 0.375  # 60 dev / 101 test

# (difficulty, intent, sql, watch_for | None)
# ---- 50 reused from Project 0: intent is the original natural-language question.
P0 = [
    ("easy", "List the names of all customers from Tunisia, ordered alphabetically by name.", "SELECT name FROM customers WHERE country = 'Tunisia' ORDER BY name;", None),
    ("easy", "What is the price of the product named 'Dune'?", "SELECT price FROM products WHERE name = 'Dune';", None),
    ("easy", "List all product names that are currently out of stock, ordered by name.", "SELECT name FROM products WHERE in_stock = 0 ORDER BY name;", None),
    ("easy", "List the 5 most expensive products with their prices, from most to least expensive.", "SELECT name, price FROM products ORDER BY price DESC LIMIT 5;", None),
    ("easy", "List all order IDs with status 'cancelled', ordered by order ID.", "SELECT order_id FROM orders WHERE status = 'cancelled' ORDER BY order_id;", None),
    ("easy", "What are the names of all categories, in alphabetical order?", "SELECT name FROM categories ORDER BY name;", None),
    ("easy", "List the names of customers who signed up in 2023, ordered by signup date.", "SELECT name FROM customers WHERE signup_date BETWEEN '2023-01-01' AND '2023-12-31' ORDER BY signup_date;", None),
    ("easy", "List all order IDs placed in March 2024, ordered by order date.", "SELECT order_id FROM orders WHERE order_date BETWEEN '2024-03-01' AND '2024-03-31' ORDER BY order_date;", None),
    ("easy", "How many products are currently in stock?", "SELECT COUNT(*) FROM products WHERE in_stock = 1;", None),
    ("easy", "List the names of customers based in London, ordered by name.", "SELECT name FROM customers WHERE city = 'London' ORDER BY name;", None),
    ("easy", "What is the average price of all products, rounded to 2 decimal places?", "SELECT ROUND(AVG(price), 2) FROM products;", None),
    ("easy", "How many orders have status 'pending'?", "SELECT COUNT(*) FROM orders WHERE status = 'pending';", None),
    ("easy", "What is the name of the most expensive product that is currently out of stock?", "SELECT name FROM products WHERE in_stock = 0 ORDER BY price DESC LIMIT 1;", "Only one row comes back even if several out-of-stock products tie on price."),
    ("easy", "How many customers signed up in each year? Show year and count, ordered by year.", "SELECT substr(signup_date, 1, 4) AS year, COUNT(*) AS n FROM customers GROUP BY year ORDER BY year;", None),
    ("easy", "What percentage of orders have status 'completed'? Round to 1 decimal place.", "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 1) FROM orders;", "The denominator is ALL orders, not only non-cancelled ones."),
    ("medium", "List all product names in the 'Electronics' category, ordered by price descending.", "SELECT p.name FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.name = 'Electronics' ORDER BY p.price DESC;", None),
    ("medium", "How many products are there in each category? Show category name and count, ordered by category name.", "SELECT c.name AS category, COUNT(*) AS n FROM products p JOIN categories c ON p.category_id = c.category_id GROUP BY c.name ORDER BY c.name;", "Categories with zero products do not appear (inner join)."),
    ("medium", "What is the average price of products in each category? Show category name and average price rounded to 2 decimals, ordered by average price descending.", "SELECT c.name AS category, ROUND(AVG(p.price), 2) AS avg_price FROM products p JOIN categories c ON p.category_id = c.category_id GROUP BY c.name ORDER BY avg_price DESC;", None),
    ("medium", "List the names of customers who have never placed an order, ordered by name.", "SELECT c.name FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id WHERE o.order_id IS NULL ORDER BY c.name;", "The LEFT JOIN + IS NULL pattern means 'customers with no orders', not 'orders with a missing id'."),
    ("medium", "How many orders has each customer placed? Show customer name and order count, ordered by order count descending, then by name.", "SELECT c.name, COUNT(o.order_id) AS n_orders FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.name ORDER BY n_orders DESC, c.name;", "Inner join: customers with zero orders are not listed. Grouping is by name, so two customers sharing a name would be merged."),
    ("medium", "List the names of products in the 'Books' category that cost less than 20, ordered by name.", "SELECT p.name FROM products p JOIN categories c ON p.category_id = c.category_id WHERE c.name = 'Books' AND p.price < 20 ORDER BY p.name;", None),
    ("medium", "What is the total quantity of 'Yoga Mat' units sold across all orders?", "SELECT SUM(oi.quantity) FROM order_items oi JOIN products p ON oi.product_id = p.product_id WHERE p.name = 'Yoga Mat';", "Counts units in every order regardless of status — cancelled orders are included."),
    ("medium", "How many orders are there for each status? Show status and count, ordered by status name.", "SELECT status, COUNT(*) AS n FROM orders GROUP BY status ORDER BY status;", None),
    ("medium", "What is the total revenue (quantity times unit price) from all order items, rounded to 2 decimals?", "SELECT ROUND(SUM(quantity * unit_price), 2) FROM order_items;", "Includes cancelled and pending orders; uses the price at time of order, not the current product price."),
    ("medium", "List the names of customers from 'France' who signed up before 2023-06-01, ordered by name.", "SELECT name FROM customers WHERE country = 'France' AND signup_date < '2023-06-01' ORDER BY name;", None),
    ("medium", "List the 5 products with the highest total quantity sold, showing product name and total quantity.", "SELECT p.name, SUM(oi.quantity) AS total_qty FROM order_items oi JOIN products p ON oi.product_id = p.product_id GROUP BY p.name ORDER BY total_qty DESC LIMIT 5;", None),
    ("medium", "List the distinct names of customers who placed at least one 'cancelled' order, ordered by name.", "SELECT DISTINCT c.name FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.status = 'cancelled' ORDER BY c.name;", None),
    ("medium", "List the names of products that have never appeared in any order, ordered by name.", "SELECT p.name FROM products p LEFT JOIN order_items oi ON p.product_id = oi.product_id WHERE oi.order_item_id IS NULL ORDER BY p.name;", None),
    ("medium", "List the top 3 customers by number of orders placed, showing name and order count.", "SELECT c.name, COUNT(*) AS n FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.name ORDER BY n DESC LIMIT 3;", "Ties beyond the third place are cut arbitrarily."),
    ("medium", "How many orders were placed in each month of 2024? Show month as YYYY-MM and count, ordered by month.", "SELECT substr(order_date, 1, 7) AS month, COUNT(*) AS n FROM orders WHERE order_date BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY month ORDER BY month;", None),
    ("medium", "List the names of customers and the date of their most recent order, for customers who have placed at least one order, ordered by most recent order date descending.", "SELECT c.name, MAX(o.order_date) AS last_order FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.name ORDER BY last_order DESC;", None),
    ("medium", "List the names of categories that have more than 5 products, with the product count, ordered by count descending.", "SELECT c.name, COUNT(*) AS n FROM products p JOIN categories c ON p.category_id = c.category_id GROUP BY c.name HAVING COUNT(*) > 5 ORDER BY n DESC;", "'More than 5' — a category with exactly 5 products is excluded."),
    ("medium", "List the names of products that cost more than the average product price, ordered by name.", "SELECT name FROM products WHERE price > (SELECT AVG(price) FROM products) ORDER BY name;", None),
    ("medium", "List the names of products priced within 10% of the most expensive product in the store, ordered by price descending.", "SELECT name FROM products WHERE price >= 0.9 * (SELECT MAX(price) FROM products) ORDER BY price DESC;", None),
    ("hard", "How many distinct products has the customer 'James Smith' ordered?", "SELECT COUNT(DISTINCT oi.product_id) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id JOIN customers c ON o.customer_id = c.customer_id WHERE c.name = 'James Smith';", "Counts different products, not units or order lines; includes cancelled orders."),
    ("hard", "List the top 5 customers by total revenue (quantity times unit price) from completed orders, showing name and revenue rounded to 2 decimals.", "SELECT c.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id WHERE o.status = 'completed' GROUP BY c.name ORDER BY revenue DESC LIMIT 5;", None),
    ("hard", "List the distinct names of customers who have ordered the product 'Ergonomic Chair', ordered by name.", "SELECT DISTINCT c.name FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id WHERE p.name = 'Ergonomic Chair' ORDER BY c.name;", None),
    ("hard", "List the names of customers who have placed 5 or more orders, with their order count, ordered by order count descending then name.", "SELECT c.name, COUNT(*) AS n FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.name HAVING COUNT(*) >= 5 ORDER BY n DESC, c.name;", None),
    ("hard", "List the names of categories that have no products priced above 100, ordered by name.", "SELECT name FROM categories cat WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.category_id = cat.category_id AND p.price > 100) ORDER BY name;", "A category with no products at all also qualifies."),
    ("hard", "For each category, what is the name and price of its most expensive product? Show category name, product name, and price, ordered by category name.", "SELECT c.name AS category, p.name AS product, p.price FROM products p JOIN categories c ON p.category_id = c.category_id WHERE p.price = (SELECT MAX(p2.price) FROM products p2 WHERE p2.category_id = p.category_id) ORDER BY c.name;", "If two products tie for the top price in a category, both are returned."),
    ("hard", "What is the total revenue (quantity times unit price) from completed orders only, rounded to 2 decimals?", "SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id WHERE o.status = 'completed';", None),
    ("hard", "Which 3 countries generated the most total revenue from completed orders? Show country and revenue rounded to 2 decimals, ordered by revenue descending.", "SELECT c.country, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id WHERE o.status = 'completed' GROUP BY c.country ORDER BY revenue DESC LIMIT 3;", None),
    ("hard", "List the names of customers whose number of orders is above the average number of orders per customer, counting only customers with at least one order, ordered by name.", "WITH counts AS (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id) SELECT c.name FROM customers c JOIN counts ct ON c.customer_id = ct.customer_id WHERE ct.n > (SELECT AVG(n) FROM counts) ORDER BY c.name;", "The average is over customers who ordered at least once, not over all customers."),
    ("hard", "List the 5 products that generated the most total revenue (quantity times unit price), showing product name and revenue rounded to 2 decimals.", "SELECT p.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id GROUP BY p.name ORDER BY revenue DESC LIMIT 5;", None),
    ("hard", "Which customers have spent more than 300 in total on completed orders? Show name and total spent rounded to 2 decimals, ordered by total spent descending.", "SELECT c.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_spent FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id WHERE o.status = 'completed' GROUP BY c.name HAVING total_spent > 300 ORDER BY total_spent DESC;", None),
    ("hard", "For each category, how many distinct customers have bought at least one product from it? Show category name and customer count, ordered by customer count descending then category name.", "SELECT cat.name, COUNT(DISTINCT o.customer_id) AS n_customers FROM categories cat JOIN products p ON p.category_id = cat.category_id JOIN order_items oi ON oi.product_id = p.product_id JOIN orders o ON o.order_id = oi.order_id GROUP BY cat.name ORDER BY n_customers DESC, cat.name;", None),
    ("hard", "List the names of customers who have ordered products from at least 3 different categories, with the category count, ordered by category count descending then name.", "SELECT c.name, COUNT(DISTINCT p.category_id) AS n_categories FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id GROUP BY c.name HAVING n_categories >= 3 ORDER BY n_categories DESC, c.name;", None),
    ("hard", "What is the name of the product that generated the single highest revenue (quantity times unit price) from a single order item row?", "SELECT p.name FROM order_items oi JOIN products p ON oi.product_id = p.product_id ORDER BY oi.quantity * oi.unit_price DESC LIMIT 1;", "This is the biggest single order line, not the product with the most total revenue."),
    ("hard", "List the names of customers who have never ordered a product from the 'Electronics' category, ordered by name.", "SELECT c.name FROM customers c WHERE c.customer_id NOT IN (SELECT o.customer_id FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id JOIN categories cat ON p.category_id = cat.category_id WHERE cat.name = 'Electronics') ORDER BY c.name;", "Customers with no orders at all are included."),
    ("hard", "What is the average order value (sum of quantity times unit price per order), rounded to 2 decimals, considering only completed orders?", "SELECT ROUND(AVG(order_total), 2) FROM (SELECT o.order_id, SUM(oi.quantity * oi.unit_price) AS order_total FROM orders o JOIN order_items oi ON o.order_id = oi.order_id WHERE o.status = 'completed' GROUP BY o.order_id);", "Average of per-order totals, not the average order-line value."),
]

# ---- 110 new for Project 1. Weighted toward queries where a fluent but
# careless explanation is easy to write and wrong — that is what makes the
# task hard to grade by exact match.
P1 = [
    # --- easy (30)
    ("easy", "Count the customers in each country.", "SELECT country, COUNT(*) FROM customers GROUP BY country;", "No ORDER BY: row order is not guaranteed."),
    ("easy", "List every distinct city customers live in, alphabetically.", "SELECT DISTINCT city FROM customers ORDER BY city;", None),
    ("easy", "Products cheaper than 10, cheapest first.", "SELECT name, price FROM products WHERE price < 10 ORDER BY price;", None),
    ("easy", "Products priced between 20 and 30 inclusive.", "SELECT name FROM products WHERE price BETWEEN 20 AND 30;", "BETWEEN includes both ends (20 and 30)."),
    ("easy", "Products whose name contains the word 'Set'.", "SELECT name FROM products WHERE name LIKE '%Set%';", "Matches 'Set' anywhere in the name, e.g. 'Knife Set', 'Building Blocks Set'."),
    ("easy", "Customers whose name starts with M.", "SELECT name FROM customers WHERE name LIKE 'M%';", None),
    ("easy", "The cheapest product.", "SELECT name, price FROM products ORDER BY price ASC LIMIT 1;", None),
    ("easy", "The 3 most recent orders.", "SELECT order_id, order_date FROM orders ORDER BY order_date DESC LIMIT 3;", None),
    ("easy", "Number of orders that are not cancelled.", "SELECT COUNT(*) FROM orders WHERE status <> 'cancelled';", "Counts both completed AND pending orders."),
    ("easy", "Customers from Egypt or Spain.", "SELECT name, country FROM customers WHERE country IN ('Egypt', 'Spain') ORDER BY country, name;", None),
    ("easy", "Customers not from Tunisia.", "SELECT name FROM customers WHERE country != 'Tunisia';", None),
    ("easy", "Highest and lowest product prices.", "SELECT MAX(price) AS highest, MIN(price) AS lowest FROM products;", None),
    ("easy", "Total number of units ever ordered.", "SELECT SUM(quantity) FROM order_items;", "Units across all orders including cancelled ones."),
    ("easy", "Number of distinct countries customers come from.", "SELECT COUNT(DISTINCT country) FROM customers;", None),
    ("easy", "The earliest signup date.", "SELECT MIN(signup_date) FROM customers;", None),
    ("easy", "Products ordered by price, positions 6 to 10.", "SELECT name, price FROM products ORDER BY price DESC LIMIT 5 OFFSET 5;", "Skips the 5 most expensive and returns the next 5 (6th to 10th most expensive)."),
    ("easy", "Show each product with a label 'expensive' if price > 50, otherwise 'affordable'.", "SELECT name, CASE WHEN price > 50 THEN 'expensive' ELSE 'affordable' END AS price_band FROM products;", "A product priced exactly 50 is 'affordable'."),
    ("easy", "Product prices with a 20% discount applied.", "SELECT name, ROUND(price * 0.8, 2) AS sale_price FROM products;", None),
    ("easy", "Orders placed in the second half of 2024.", "SELECT order_id FROM orders WHERE order_date >= '2024-07-01';", None),
    ("easy", "Customers who signed up in the month of January (any year).", "SELECT name, signup_date FROM customers WHERE strftime('%m', signup_date) = '01';", "Any year, not only one specific January."),
    ("easy", "Order line items with quantity 3.", "SELECT order_item_id, order_id, product_id FROM order_items WHERE quantity = 3;", None),
    ("easy", "Number of order lines per quantity value.", "SELECT quantity, COUNT(*) AS n_lines FROM order_items GROUP BY quantity ORDER BY quantity;", "Counts order lines, not orders or units."),
    ("easy", "In-stock products under 15.", "SELECT name FROM products WHERE in_stock = 1 AND price < 15 ORDER BY name;", None),
    ("easy", "Products that are out of stock or cost more than 100.", "SELECT name FROM products WHERE in_stock = 0 OR price > 100;", "OR, not AND: either condition is enough."),
    ("easy", "Customer names in upper case.", "SELECT UPPER(name) FROM customers;", None),
    ("easy", "Length of each product name, longest first.", "SELECT name, LENGTH(name) AS len FROM products ORDER BY len DESC;", None),
    ("easy", "Sum of all current product prices.", "SELECT SUM(price) FROM products;", "Adds up the catalogue list prices, not sales revenue."),
    ("easy", "Number of order lines whose unit price differs from the product's current price.", "SELECT COUNT(*) FROM order_items oi WHERE oi.unit_price <> (SELECT price FROM products p WHERE p.product_id = oi.product_id);", None),
    ("easy", "Integer average quantity per order line.", "SELECT SUM(quantity) / COUNT(*) FROM order_items;", "Integer division in SQLite: the result is truncated to a whole number."),
    ("easy", "Customers who signed up in 2022, most recent first.", "SELECT name FROM customers WHERE signup_date LIKE '2022-%' ORDER BY signup_date DESC;", None),

    # --- medium (40)
    ("medium", "Number of orders per customer, including customers with none.", "SELECT c.name, COUNT(o.order_id) AS n_orders FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id ORDER BY n_orders;", "COUNT(o.order_id) gives 0 for customers without orders; COUNT(*) would give 1."),
    ("medium", "Customers with the number of their orders, but using COUNT(*) on a LEFT JOIN.", "SELECT c.name, COUNT(*) AS n FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id;", "COUNT(*) counts rows: a customer with no orders would show 1, not 0."),
    ("medium", "Customers joined with their completed orders only, keeping customers without any.", "SELECT c.name, o.order_id FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'completed';", "The status filter is in the ON clause: every customer is kept, with NULL order_id if they have no completed order."),
    ("medium", "Customers joined with their orders, filtered to completed orders.", "SELECT c.name, o.order_id FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE o.status = 'completed';", "The WHERE filter on the right table turns the LEFT JOIN into an inner join: customers with no completed order disappear."),
    ("medium", "Revenue per order status.", "SELECT o.status, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.status;", None),
    ("medium", "Number of items (lines) in each order, biggest orders first.", "SELECT order_id, COUNT(*) AS n_lines FROM order_items GROUP BY order_id ORDER BY n_lines DESC, order_id;", "Counts distinct product lines per order, not units."),
    ("medium", "Orders with more than 5 units in total.", "SELECT order_id, SUM(quantity) AS units FROM order_items GROUP BY order_id HAVING SUM(quantity) > 5;", None),
    ("medium", "Average quantity per order line for each product category.", "SELECT c.name, AVG(oi.quantity) FROM order_items oi JOIN products p ON p.product_id = oi.product_id JOIN categories c ON c.category_id = p.category_id GROUP BY c.name;", None),
    ("medium", "Countries with at least 3 customers.", "SELECT country, COUNT(*) AS n FROM customers GROUP BY country HAVING n >= 3 ORDER BY n DESC;", None),
    ("medium", "Customers who signed up after the most recent signup from Tunisia.", "SELECT name FROM customers WHERE signup_date > (SELECT MAX(signup_date) FROM customers WHERE country = 'Tunisia');", None),
    ("medium", "Products never ordered, using NOT IN.", "SELECT name FROM products WHERE product_id NOT IN (SELECT product_id FROM order_items);", None),
    ("medium", "Customers who have at least one pending order, using EXISTS.", "SELECT name FROM customers c WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id AND o.status = 'pending');", None),
    ("medium", "Customers whose every order is completed (and who have at least one order).", "SELECT c.name FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id HAVING SUM(o.status <> 'completed') = 0;", "SUM of a boolean counts non-completed orders; requiring 0 means ALL their orders are completed."),
    ("medium", "Order count per month name for 2024.", "SELECT strftime('%m', order_date) AS month, COUNT(*) FROM orders WHERE strftime('%Y', order_date) = '2024' GROUP BY month ORDER BY month;", None),
    ("medium", "Orders with the customer's country.", "SELECT o.order_id, o.order_date, c.country FROM orders o JOIN customers c ON c.customer_id = o.customer_id ORDER BY o.order_date;", None),
    ("medium", "Days between signup and first order for each customer.", "SELECT c.name, julianday(MIN(o.order_date)) - julianday(c.signup_date) AS days_to_first_order FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id;", "Can be negative: orders in this data can predate the signup date."),
    ("medium", "Categories and their number of in-stock products.", "SELECT c.name, SUM(p.in_stock) AS in_stock_count FROM categories c JOIN products p ON p.category_id = c.category_id GROUP BY c.name;", "SUM(in_stock) counts in-stock products because in_stock is 0/1."),
    ("medium", "Share of each category in the product catalogue, in percent.", "SELECT c.name, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM products), 1) AS pct FROM products p JOIN categories c ON c.category_id = p.category_id GROUP BY c.name;", None),
    ("medium", "Most expensive product in each category (SQLite bare-column trick).", "SELECT c.name, p.name, MAX(p.price) FROM products p JOIN categories c ON c.category_id = p.category_id GROUP BY c.name;", "SQLite-specific: the bare p.name comes from the row holding the MAX. Ties return only one product."),
    ("medium", "Customers with a comma-separated list of their order ids.", "SELECT c.name, GROUP_CONCAT(o.order_id) AS order_ids FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id;", None),
    ("medium", "Cities with more than one customer.", "SELECT city, COUNT(*) FROM customers GROUP BY city HAVING COUNT(*) > 1;", None),
    ("medium", "Products and how many times they were ordered, including never-ordered products.", "SELECT p.name, COUNT(oi.order_item_id) AS times_ordered FROM products p LEFT JOIN order_items oi ON oi.product_id = p.product_id GROUP BY p.product_id ORDER BY times_ordered DESC;", "Counts order lines (how many orders included the product), not units."),
    ("medium", "Units sold per product, excluding cancelled orders.", "SELECT p.name, SUM(oi.quantity) AS units FROM products p JOIN order_items oi ON oi.product_id = p.product_id JOIN orders o ON o.order_id = oi.order_id WHERE o.status != 'cancelled' GROUP BY p.name ORDER BY units DESC;", None),
    ("medium", "Customers who ordered in both January and December 2024.", "SELECT customer_id FROM orders WHERE order_date LIKE '2024-01-%' INTERSECT SELECT customer_id FROM orders WHERE order_date LIKE '2024-12-%';", None),
    ("medium", "Customer ids who have placed orders but never had a cancelled order.", "SELECT customer_id FROM orders EXCEPT SELECT customer_id FROM orders WHERE status = 'cancelled';", "Removes any customer who has even one cancelled order."),
    ("medium", "All customer and product names in one list.", "SELECT name FROM customers UNION SELECT name FROM products;", "UNION removes duplicates (UNION ALL would keep them)."),
    ("medium", "All customer cities and all country names, keeping duplicates.", "SELECT city FROM customers UNION ALL SELECT country FROM customers;", None),
    ("medium", "Order totals for pending orders.", "SELECT o.order_id, SUM(oi.quantity * oi.unit_price) AS total FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'pending' GROUP BY o.order_id ORDER BY total DESC;", None),
    ("medium", "Average number of lines per order.", "SELECT AVG(n) FROM (SELECT order_id, COUNT(*) AS n FROM order_items GROUP BY order_id);", None),
    ("medium", "Products more expensive than every product in the Books category.", "SELECT name FROM products WHERE price > (SELECT MAX(p.price) FROM products p JOIN categories c ON c.category_id = p.category_id WHERE c.name = 'Books');", None),
    ("medium", "Customers' first order date.", "SELECT c.name, MIN(o.order_date) AS first_order FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id ORDER BY first_order;", None),
    ("medium", "Number of orders per weekday (0 = Sunday).", "SELECT strftime('%w', order_date) AS weekday, COUNT(*) FROM orders GROUP BY weekday ORDER BY weekday;", None),
    ("medium", "Customers and their country's customer count.", "SELECT name, country, (SELECT COUNT(*) FROM customers c2 WHERE c2.country = c1.country) AS same_country FROM customers c1;", "Correlated subquery: the count includes the customer themselves."),
    ("medium", "Cancelled-order ratio per customer.", "SELECT customer_id, AVG(status = 'cancelled') AS cancel_rate FROM orders GROUP BY customer_id ORDER BY cancel_rate DESC;", "AVG of a 0/1 condition is the fraction of that customer's orders that are cancelled."),
    ("medium", "Products whose price is above their category average.", "SELECT p.name, p.price FROM products p WHERE p.price > (SELECT AVG(p2.price) FROM products p2 WHERE p2.category_id = p.category_id);", "Compared with the average of their OWN category, not the store-wide average."),
    ("medium", "Customer count per country, with unknown country shown as 'n/a'.", "SELECT COALESCE(country, 'n/a') AS country, COUNT(*) FROM customers GROUP BY 1;", None),
    ("medium", "The second most expensive distinct price.", "SELECT DISTINCT price FROM products ORDER BY price DESC LIMIT 1 OFFSET 1;", None),
    ("medium", "Orders placed on the same day as another order.", "SELECT DISTINCT o1.order_id, o1.order_date FROM orders o1 JOIN orders o2 ON o1.order_date = o2.order_date AND o1.order_id <> o2.order_id ORDER BY o1.order_date;", None),
    ("medium", "Categories with no product currently out of stock.", "SELECT c.name FROM categories c JOIN products p ON p.category_id = c.category_id GROUP BY c.name HAVING MIN(p.in_stock) = 1;", "MIN(in_stock)=1 means every product in the category is in stock."),
    ("medium", "Customers who ordered the same product more than once (across orders).", "SELECT c.name, p.name, COUNT(*) AS times FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.product_id = oi.product_id GROUP BY c.customer_id, p.product_id HAVING COUNT(*) > 1;", None),

    # --- hard (40)
    ("hard", "Rank products by price within their category.", "SELECT c.name AS category, p.name, p.price, RANK() OVER (PARTITION BY p.category_id ORDER BY p.price DESC) AS price_rank FROM products p JOIN categories c ON c.category_id = p.category_id;", "RANK gives ties the same rank and skips the next number."),
    ("hard", "Top 2 most expensive products per category.", "SELECT category, name, price FROM (SELECT c.name AS category, p.name, p.price, ROW_NUMBER() OVER (PARTITION BY p.category_id ORDER BY p.price DESC) AS rn FROM products p JOIN categories c ON c.category_id = p.category_id) WHERE rn <= 2;", "ROW_NUMBER breaks ties arbitrarily: exactly 2 per category (or fewer)."),
    ("hard", "Running total of revenue by order date.", "WITH daily AS (SELECT o.order_date, SUM(oi.quantity * oi.unit_price) AS rev FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.order_date) SELECT order_date, rev, SUM(rev) OVER (ORDER BY order_date) AS running_total FROM daily;", None),
    ("hard", "Each customer's orders numbered in date order.", "SELECT customer_id, order_id, order_date, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS nth_order FROM orders;", None),
    ("hard", "Days since each customer's previous order.", "SELECT customer_id, order_id, order_date, julianday(order_date) - julianday(LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date)) AS gap_days FROM orders;", "The first order of each customer has a NULL gap."),
    ("hard", "Monthly revenue and month-over-month change for completed orders.", "WITH m AS (SELECT substr(o.order_date, 1, 7) AS month, SUM(oi.quantity * oi.unit_price) AS rev FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'completed' GROUP BY month) SELECT month, ROUND(rev, 2), ROUND(rev - LAG(rev) OVER (ORDER BY month), 2) AS change FROM m;", None),
    ("hard", "Each product's share of its category's revenue.", "WITH pr AS (SELECT p.product_id, p.name, p.category_id, SUM(oi.quantity * oi.unit_price) AS rev FROM products p JOIN order_items oi ON oi.product_id = p.product_id GROUP BY p.product_id) SELECT name, ROUND(100.0 * rev / SUM(rev) OVER (PARTITION BY category_id), 1) AS pct_of_category FROM pr;", None),
    ("hard", "Customers whose total spend is in the top 25%.", "WITH spend AS (SELECT o.customer_id, SUM(oi.quantity * oi.unit_price) AS total FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.customer_id) SELECT c.name, total FROM (SELECT customer_id, total, NTILE(4) OVER (ORDER BY total DESC) AS quartile FROM spend) s JOIN customers c ON c.customer_id = s.customer_id WHERE quartile = 1;", "Spend includes all statuses, including cancelled orders."),
    ("hard", "Customers who never ordered a product from category 1 (Electronics).", "SELECT name FROM customers WHERE customer_id NOT IN (SELECT o.customer_id FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.order_id LEFT JOIN products p ON p.product_id = oi.product_id WHERE p.category_id = 1);", "Includes customers who never placed any order."),
    ("hard", "Products that have been bought by customers from at least 3 countries.", "SELECT p.name, COUNT(DISTINCT c.country) AS n_countries FROM products p JOIN order_items oi ON oi.product_id = p.product_id JOIN orders o ON o.order_id = oi.order_id JOIN customers c ON c.customer_id = o.customer_id GROUP BY p.product_id HAVING n_countries >= 3 ORDER BY n_countries DESC;", None),
    ("hard", "Customers who bought every product in the Beauty category.", "SELECT c.name FROM customers c WHERE NOT EXISTS (SELECT 1 FROM products p WHERE p.category_id = (SELECT category_id FROM categories WHERE name = 'Beauty') AND NOT EXISTS (SELECT 1 FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.customer_id = c.customer_id AND oi.product_id = p.product_id));", "Double NOT EXISTS = relational division: 'there is no Beauty product this customer has NOT bought'."),
    ("hard", "Pairs of products bought together in the same order, most frequent first.", "SELECT p1.name, p2.name, COUNT(*) AS together FROM order_items a JOIN order_items b ON a.order_id = b.order_id AND a.product_id < b.product_id JOIN products p1 ON p1.product_id = a.product_id JOIN products p2 ON p2.product_id = b.product_id GROUP BY a.product_id, b.product_id ORDER BY together DESC LIMIT 10;", "a.product_id < b.product_id counts each pair once and excludes pairing a product with itself."),
    ("hard", "Customers whose first order was cancelled.", "WITH firsts AS (SELECT customer_id, MIN(order_date) AS first_date FROM orders GROUP BY customer_id) SELECT DISTINCT c.name FROM firsts f JOIN orders o ON o.customer_id = f.customer_id AND o.order_date = f.first_date JOIN customers c ON c.customer_id = f.customer_id WHERE o.status = 'cancelled';", "If two orders fall on the first date, the customer qualifies if either is cancelled."),
    ("hard", "Revenue by country and category, only combinations above 200.", "SELECT c.country, cat.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS rev FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.product_id = oi.product_id JOIN categories cat ON cat.category_id = p.category_id GROUP BY c.country, cat.name HAVING rev > 200 ORDER BY rev DESC;", None),
    ("hard", "Customers who spent more in completed orders than the average customer.", "WITH t AS (SELECT o.customer_id, SUM(oi.quantity * oi.unit_price) AS spent FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'completed' GROUP BY o.customer_id) SELECT c.name, ROUND(t.spent, 2) FROM t JOIN customers c ON c.customer_id = t.customer_id WHERE t.spent > (SELECT AVG(spent) FROM t) ORDER BY t.spent DESC;", None),
    ("hard", "Share of revenue lost to cancellations, per country.", "SELECT c.country, ROUND(100.0 * SUM(CASE WHEN o.status = 'cancelled' THEN oi.quantity * oi.unit_price ELSE 0 END) / SUM(oi.quantity * oi.unit_price), 1) AS pct_cancelled FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id GROUP BY c.country ORDER BY pct_cancelled DESC;", "A share of order VALUE, not a share of the number of orders."),
    ("hard", "Number of customers by number of orders placed (a histogram).", "SELECT n_orders, COUNT(*) AS n_customers FROM (SELECT customer_id, COUNT(*) AS n_orders FROM orders GROUP BY customer_id) GROUP BY n_orders ORDER BY n_orders;", None),
    ("hard", "The largest order (by value) for each customer.", "WITH ot AS (SELECT o.customer_id, o.order_id, SUM(oi.quantity * oi.unit_price) AS total FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.order_id) SELECT c.name, ot.order_id, ot.total FROM ot JOIN customers c ON c.customer_id = ot.customer_id WHERE ot.total = (SELECT MAX(total) FROM ot ot2 WHERE ot2.customer_id = ot.customer_id);", None),
    ("hard", "Products whose sales in the second half of 2024 exceeded the first half.", "SELECT p.name, SUM(CASE WHEN o.order_date < '2024-07-01' THEN oi.quantity ELSE 0 END) AS h1, SUM(CASE WHEN o.order_date >= '2024-07-01' THEN oi.quantity ELSE 0 END) AS h2 FROM products p JOIN order_items oi ON oi.product_id = p.product_id JOIN orders o ON o.order_id = oi.order_id GROUP BY p.product_id HAVING h2 > h1;", "Compares units, not revenue."),
    ("hard", "Customers with orders in at least 6 distinct months.", "SELECT c.name, COUNT(DISTINCT substr(o.order_date, 1, 7)) AS active_months FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id HAVING active_months >= 6 ORDER BY active_months DESC;", None),
    ("hard", "Orders where every line is from the same category.", "SELECT oi.order_id FROM order_items oi JOIN products p ON p.product_id = oi.product_id GROUP BY oi.order_id HAVING COUNT(DISTINCT p.category_id) = 1;", "Includes single-line orders, which trivially qualify."),
    ("hard", "Customers whose average order value is above 100, counting only completed orders.", "SELECT c.name, ROUND(AVG(ot.total), 2) AS avg_order FROM customers c JOIN (SELECT o.order_id, o.customer_id, SUM(oi.quantity * oi.unit_price) AS total FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'completed' GROUP BY o.order_id) ot ON ot.customer_id = c.customer_id GROUP BY c.customer_id HAVING AVG(ot.total) > 100;", None),
    ("hard", "The most popular category in each country by units sold.", "WITH cc AS (SELECT c.country, cat.name AS category, SUM(oi.quantity) AS units FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.product_id = oi.product_id JOIN categories cat ON cat.category_id = p.category_id GROUP BY c.country, cat.name) SELECT country, category, units FROM (SELECT *, RANK() OVER (PARTITION BY country ORDER BY units DESC) AS r FROM cc) WHERE r = 1;", "RANK = 1 can return several categories for a country if they tie."),
    ("hard", "Cumulative number of signups over time.", "SELECT signup_date, COUNT(*) OVER (ORDER BY signup_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative FROM customers ORDER BY signup_date;", None),
    ("hard", "Three-order moving average of order value for each customer.", "WITH ot AS (SELECT o.customer_id, o.order_id, o.order_date, SUM(oi.quantity * oi.unit_price) AS total FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.order_id) SELECT customer_id, order_id, ROUND(AVG(total) OVER (PARTITION BY customer_id ORDER BY order_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg FROM ot;", "Window covers the current order and up to 2 before it, per customer."),
    ("hard", "Customers who ordered a product priced above 100 and also one below 10.", "SELECT c.name FROM customers c WHERE EXISTS (SELECT 1 FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.customer_id = c.customer_id AND oi.unit_price > 100) AND EXISTS (SELECT 1 FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.customer_id = c.customer_id AND oi.unit_price < 10);", "Uses the price paid (unit_price), not the current catalogue price. The two purchases may be in different orders."),
    ("hard", "Percentage of each customer's orders that include an Electronics item.", "SELECT o.customer_id, ROUND(100.0 * COUNT(DISTINCT CASE WHEN p.category_id = 1 THEN o.order_id END) / COUNT(DISTINCT o.order_id), 1) AS pct FROM orders o JOIN order_items oi ON oi.order_id = o.order_id JOIN products p ON p.product_id = oi.product_id GROUP BY o.customer_id;", "category_id 1 is Electronics; CASE without ELSE yields NULL, which COUNT ignores."),
    ("hard", "Products whose current price is higher than any price they were sold at.", "SELECT p.name, p.price, MAX(oi.unit_price) AS max_paid FROM products p JOIN order_items oi ON oi.product_id = p.product_id GROUP BY p.product_id HAVING p.price > MAX(oi.unit_price);", "Never-ordered products are excluded by the inner join."),
    ("hard", "Order count for each calendar month 1-12, including months without orders.", "WITH RECURSIVE months(m) AS (SELECT 1 UNION ALL SELECT m + 1 FROM months WHERE m < 12) SELECT m, (SELECT COUNT(*) FROM orders WHERE CAST(strftime('%m', order_date) AS INTEGER) = m) AS n_orders FROM months;", "Counts orders in that calendar month across all years, and shows 0 for empty months."),
    ("hard", "Customers ranked by revenue within their country, top one per country.", "WITH r AS (SELECT c.country, c.name, SUM(oi.quantity * oi.unit_price) AS rev FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'completed' GROUP BY c.customer_id) SELECT country, name, ROUND(rev, 2) FROM (SELECT *, DENSE_RANK() OVER (PARTITION BY country ORDER BY rev DESC) AS dr FROM r) WHERE dr = 1 ORDER BY rev DESC;", None),
    ("hard", "Orders whose value is more than double the customer's average order value.", "WITH ot AS (SELECT o.customer_id, o.order_id, SUM(oi.quantity * oi.unit_price) AS total FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.order_id) SELECT order_id, customer_id, total FROM ot WHERE total > 2 * (SELECT AVG(total) FROM ot x WHERE x.customer_id = ot.customer_id);", None),
    ("hard", "Categories whose revenue from completed orders fell in Q4 compared with Q3 2024.", "SELECT cat.name, SUM(CASE WHEN o.order_date BETWEEN '2024-07-01' AND '2024-09-30' THEN oi.quantity * oi.unit_price ELSE 0 END) AS q3, SUM(CASE WHEN o.order_date BETWEEN '2024-10-01' AND '2024-12-31' THEN oi.quantity * oi.unit_price ELSE 0 END) AS q4 FROM categories cat JOIN products p ON p.category_id = cat.category_id JOIN order_items oi ON oi.product_id = p.product_id JOIN orders o ON o.order_id = oi.order_id WHERE o.status = 'completed' GROUP BY cat.name HAVING q4 < q3;", None),
    ("hard", "Customers with no order in the last 90 days of 2024.", "SELECT name FROM customers c WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id AND o.order_date > date('2024-12-31', '-90 days'));", "Includes customers who never ordered at all."),
    ("hard", "Median product price.", "SELECT AVG(price) FROM (SELECT price FROM products ORDER BY price LIMIT 2 - (SELECT COUNT(*) FROM products) % 2 OFFSET ((SELECT COUNT(*) FROM products) - 1) / 2);", "Averages the middle one or two prices depending on whether the count is odd or even."),
    ("hard", "Number of repeat customers (more than one completed order) per country.", "SELECT c.country, COUNT(*) AS repeat_customers FROM customers c WHERE (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id AND o.status = 'completed') > 1 GROUP BY c.country ORDER BY repeat_customers DESC;", "Countries with zero repeat customers do not appear."),
    ("hard", "Each order's value and its percentage of the customer's lifetime spend.", "WITH ot AS (SELECT o.customer_id, o.order_id, SUM(oi.quantity * oi.unit_price) AS total FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.order_id) SELECT customer_id, order_id, ROUND(total, 2), ROUND(100.0 * total / SUM(total) OVER (PARTITION BY customer_id), 1) AS pct_of_lifetime FROM ot ORDER BY customer_id, pct_of_lifetime DESC;", "Lifetime spend here includes cancelled and pending orders."),
    ("hard", "Products that were only ever bought by customers from a single country.", "SELECT p.name, MIN(c.country) AS only_country FROM products p JOIN order_items oi ON oi.product_id = p.product_id JOIN orders o ON o.order_id = oi.order_id JOIN customers c ON c.customer_id = o.customer_id GROUP BY p.product_id HAVING COUNT(DISTINCT c.country) = 1;", None),
    ("hard", "The day with the highest revenue and its revenue.", "SELECT o.order_date, SUM(oi.quantity * oi.unit_price) AS rev FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.order_date ORDER BY rev DESC LIMIT 1;", "All statuses count, including cancelled."),
    ("hard", "Customers whose spend grew every quarter of 2024 (no quarter lower than the one before).", "WITH q AS (SELECT o.customer_id, (CAST(strftime('%m', o.order_date) AS INTEGER) + 2) / 3 AS qtr, SUM(oi.quantity * oi.unit_price) AS rev FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY o.customer_id, qtr), d AS (SELECT customer_id, rev - LAG(rev) OVER (PARTITION BY customer_id ORDER BY qtr) AS delta FROM q) SELECT customer_id FROM d GROUP BY customer_id HAVING MIN(COALESCE(delta, 0)) >= 0;", "Only quarters where the customer actually ordered are compared; a quarter with no orders is skipped, not treated as 0."),
    ("hard", "Average basket size (units per order) by country, completed orders only.", "SELECT c.country, ROUND(1.0 * SUM(oi.quantity) / COUNT(DISTINCT o.order_id), 2) AS units_per_order FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id WHERE o.status = 'completed' GROUP BY c.country ORDER BY units_per_order DESC;", "1.0 * forces decimal division; COUNT(DISTINCT order_id) avoids counting an order once per line."),
    ("hard", "Products whose units sold are above the average units sold per product.", "WITH u AS (SELECT product_id, SUM(quantity) AS units FROM order_items GROUP BY product_id) SELECT p.name, u.units FROM u JOIN products p ON p.product_id = u.product_id WHERE u.units > (SELECT AVG(units) FROM u) ORDER BY u.units DESC;", "Average over products that sold at least once."),
]



def build() -> list[dict]:
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} missing — run `python db/build_db.py` first.")
    conn = sqlite3.connect(DB_PATH)

    rows = []
    for origin, block in (("p0", P0), ("p1", P1)):
        for difficulty, intent, sql, watch_for in block:
            try:
                n_rows = len(conn.execute(sql).fetchall())
            except sqlite3.Error as e:
                raise SystemExit(f"Query failed ({origin}, {intent!r}): {e}\n{sql}")
            rows.append({
                "difficulty": difficulty,
                "sql": sql,
                "intent": intent,
                "watch_for": watch_for,
                "origin": origin,
                "n_result_rows": n_rows,
            })
    conn.close()

    sqls = [r["sql"] for r in rows]
    dupes = {s for s in sqls if sqls.count(s) > 1}
    if dupes:
        raise SystemExit(f"Duplicate SQL: {dupes}")

    for i, r in enumerate(rows, start=1):
        r["id"] = f"q{i:03d}"

    # Stratified split: same dev fraction inside each difficulty.
    rng = random.Random(SPLIT_SEED)
    for diff in ("easy", "medium", "hard"):
        group = [r for r in rows if r["difficulty"] == diff]
        rng.shuffle(group)
        n_dev = round(len(group) * DEV_FRACTION)
        for j, r in enumerate(group):
            r["split"] = "dev" if j < n_dev else "test"

    order = ["id", "split", "difficulty", "origin", "sql", "intent", "watch_for", "n_result_rows"]
    return [{k: r[k] for k in order} for r in rows]


def main() -> None:
    rows = build()
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = {}
    for r in rows:
        by.setdefault((r["split"], r["difficulty"]), 0)
        by[(r["split"], r["difficulty"])] += 1
    print(f"Wrote {len(rows)} queries to {OUT_PATH.relative_to(ROOT)}")
    for split in ("dev", "test"):
        parts = ", ".join(f"{d}={by.get((split, d), 0)}" for d in ("easy", "medium", "hard"))
        print(f"  {split}: {sum(v for (s, _), v in by.items() if s == split)}  ({parts})")
    zero = [r["id"] for r in rows if r["n_result_rows"] == 0]
    print(f"  queries returning 0 rows (kept on purpose, see LABELLING_GUIDE.md): {zero}")


if __name__ == "__main__":
    main()
