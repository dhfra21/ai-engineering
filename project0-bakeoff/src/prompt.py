"""The one prompt used for all three models. Keep it byte-for-byte identical
across models — the brief explicitly forbids a different prompt per model.
"""
from __future__ import annotations

SCHEMA_TEXT = """\
Table categories(category_id INTEGER PK, name TEXT)
Table customers(customer_id INTEGER PK, name TEXT, city TEXT, country TEXT, signup_date TEXT "YYYY-MM-DD")
Table products(product_id INTEGER PK, name TEXT, category_id INTEGER FK->categories.category_id, price REAL, in_stock INTEGER "0 or 1")
Table orders(order_id INTEGER PK, customer_id INTEGER FK->customers.customer_id, order_date TEXT "YYYY-MM-DD", status TEXT "completed|pending|cancelled")
Table order_items(order_item_id INTEGER PK, order_id INTEGER FK->orders.order_id, product_id INTEGER FK->products.product_id, quantity INTEGER, unit_price REAL)
"""

SYSTEM_PROMPT = "You are a SQL generator. You only output SQL. You never explain, never apologize, never add commentary."

USER_TEMPLATE = """\
Database schema (SQLite):
{schema}

Write a single SQLite SELECT statement that answers this question:
"{question}"

Rules:
- Output ONLY the SQL statement. No markdown code fences, no explanation, no leading/trailing text.
- Use only SELECT. Never write INSERT, UPDATE, DELETE, DROP, ALTER, or any other statement.
- Use only the tables and columns listed above.
- End the statement with a semicolon.
"""


def build_prompt(question: str) -> str:
    return USER_TEMPLATE.format(schema=SCHEMA_TEXT, question=question)
