"""Build the deterministic SQLite database for the Project 0 bake-off.

Run:
    python db/build_db.py

Recreates db/store.db from scratch every time (safe to re-run). All data is
generated with a fixed random seed so the database — and therefore every
gold SQL answer in data/items.jsonl — is reproducible from a clean clone.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SEED = 42
DB_PATH = Path(__file__).parent / "store.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

CATEGORIES = [
    "Electronics", "Books", "Home & Kitchen", "Sports",
    "Toys", "Beauty", "Grocery", "Office",
]

# (product name, category, base price)
PRODUCTS = [
    ("Wireless Mouse", "Electronics", 19.99),
    ("Mechanical Keyboard", "Electronics", 59.99),
    ("USB-C Hub", "Electronics", 24.50),
    ("Noise Cancelling Headphones", "Electronics", 129.00),
    ("Bluetooth Speaker", "Electronics", 45.00),
    ("Webcam 1080p", "Electronics", 34.99),
    ("Portable SSD 1TB", "Electronics", 89.00),
    ("Smartwatch", "Electronics", 149.99),
    ("The Pragmatic Programmer", "Books", 34.99),
    ("Clean Code", "Books", 29.99),
    ("Atomic Habits", "Books", 16.99),
    ("Dune", "Books", 12.50),
    ("A Brief History of Time", "Books", 14.99),
    ("Cooking for Beginners", "Books", 18.00),
    ("Nonstick Frying Pan", "Home & Kitchen", 22.99),
    ("Electric Kettle", "Home & Kitchen", 27.50),
    ("Knife Set", "Home & Kitchen", 39.99),
    ("Blender", "Home & Kitchen", 44.00),
    ("Bed Sheets Queen", "Home & Kitchen", 32.99),
    ("Vacuum Cleaner", "Home & Kitchen", 119.99),
    ("Yoga Mat", "Sports", 21.99),
    ("Dumbbell Set 20kg", "Sports", 65.00),
    ("Running Shoes", "Sports", 79.99),
    ("Cycling Helmet", "Sports", 38.50),
    ("Tennis Racket", "Sports", 54.99),
    ("Building Blocks Set", "Toys", 29.99),
    ("Remote Control Car", "Toys", 42.00),
    ("Puzzle 1000pc", "Toys", 15.99),
    ("Board Game Classic", "Toys", 24.99),
    ("Moisturizing Cream", "Beauty", 18.50),
    ("Shampoo 500ml", "Beauty", 9.99),
    ("Electric Toothbrush", "Beauty", 34.99),
    ("Perfume 50ml", "Beauty", 55.00),
    ("Olive Oil 1L", "Grocery", 11.99),
    ("Organic Coffee 1kg", "Grocery", 16.50),
    ("Pasta 500g", "Grocery", 2.49),
    ("Green Tea Box", "Grocery", 6.99),
    ("Desk Lamp", "Office", 26.99),
    ("Ergonomic Chair", "Office", 189.00),
    ("Notebook Pack", "Office", 8.99),
]

# (name, city, country)
CUSTOMERS = [
    ("Yasmine Ben Salah", "Tunis", "Tunisia"),
    ("Karim Trabelsi", "Sfax", "Tunisia"),
    ("Amel Gharbi", "Sousse", "Tunisia"),
    ("Mohamed Jendoubi", "Tunis", "Tunisia"),
    ("Sarra Cherif", "Bizerte", "Tunisia"),
    ("Walid Mansour", "Tunis", "Tunisia"),
    ("Nour Ayari", "Sfax", "Tunisia"),
    ("Firas Bouazizi", "Gabes", "Tunisia"),
    ("Emma Laurent", "Paris", "France"),
    ("Lucas Bernard", "Lyon", "France"),
    ("Chloe Dubois", "Paris", "France"),
    ("Hugo Martin", "Marseille", "France"),
    ("Marco Rossi", "Milan", "Italy"),
    ("Giulia Ferrari", "Rome", "Italy"),
    ("Luca Romano", "Turin", "Italy"),
    ("Hans Mueller", "Berlin", "Germany"),
    ("Anna Schmidt", "Munich", "Germany"),
    ("Peter Weber", "Hamburg", "Germany"),
    ("James Smith", "London", "UK"),
    ("Olivia Jones", "Manchester", "UK"),
    ("William Brown", "London", "UK"),
    ("Fatima Al-Sayed", "Cairo", "Egypt"),
    ("Omar Khalil", "Cairo", "Egypt"),
    ("Layla Hassan", "Alexandria", "Egypt"),
    ("Sofia Garcia", "Madrid", "Spain"),
    ("Diego Fernandez", "Barcelona", "Spain"),
    ("Maria Lopez", "Madrid", "Spain"),
    ("John Miller", "Boston", "USA"),
    ("Emily Davis", "New York", "USA"),
    ("Michael Wilson", "Chicago", "USA"),
]

STATUSES = ["completed", "completed", "completed", "pending", "cancelled"]


def random_date(rng: random.Random, start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=rng.randint(0, delta))).isoformat()


def build() -> None:
    rng = random.Random(SEED)

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    cat_ids = {}
    for i, name in enumerate(CATEGORIES, start=1):
        conn.execute("INSERT INTO categories (category_id, name) VALUES (?, ?)", (i, name))
        cat_ids[name] = i

    for i, (name, city, country) in enumerate(CUSTOMERS, start=1):
        signup = random_date(rng, date(2022, 1, 1), date(2024, 6, 30))
        conn.execute(
            "INSERT INTO customers (customer_id, name, city, country, signup_date) VALUES (?, ?, ?, ?, ?)",
            (i, name, city, country, signup),
        )

    product_ids = []
    for i, (name, cat, price) in enumerate(PRODUCTS, start=1):
        in_stock = 1 if rng.random() > 0.15 else 0
        conn.execute(
            "INSERT INTO products (product_id, name, category_id, price, in_stock) VALUES (?, ?, ?, ?, ?)",
            (i, name, cat_ids[cat], price, in_stock),
        )
        product_ids.append(i)

    n_customers = len(CUSTOMERS)
    order_id = 1
    order_item_id = 1
    for _ in range(160):
        customer_id = rng.randint(1, n_customers)
        order_date = random_date(rng, date(2024, 1, 1), date(2024, 12, 31))
        status = rng.choice(STATUSES)
        conn.execute(
            "INSERT INTO orders (order_id, customer_id, order_date, status) VALUES (?, ?, ?, ?)",
            (order_id, customer_id, order_date, status),
        )
        n_items = rng.randint(1, 4)
        chosen = rng.sample(product_ids, k=n_items)
        for pid in chosen:
            base_price = PRODUCTS[pid - 1][2]
            qty = rng.randint(1, 3)
            conn.execute(
                "INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price) "
                "VALUES (?, ?, ?, ?, ?)",
                (order_item_id, order_id, pid, qty, base_price),
            )
            order_item_id += 1
        order_id += 1

    conn.commit()
    conn.close()
    print(f"Built {DB_PATH} — {n_customers} customers, {len(PRODUCTS)} products, "
          f"{order_id - 1} orders, {order_item_id - 1} order_items.")


if __name__ == "__main__":
    build()
