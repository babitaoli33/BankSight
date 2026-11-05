"""Build a small SQLite database with the same core tables as the Kaggle dataset.

The real data (~650MB) is not in the repo, so tests, CI and quick demos use this
generated sample instead:

    python -m assistant.sample_db            # writes data/sample/bank_sample.db
"""

from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "sample" / "bank_sample.db"

SCHEMA = """
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT,
                        credit_score INTEGER, created_at TEXT);
CREATE TABLE accounts (account_id INTEGER PRIMARY KEY, customer_id INTEGER, account_type TEXT,
                       balance_usd REAL, open_date TEXT);
CREATE TABLE cards (card_id INTEGER PRIMARY KEY, account_id INTEGER, card_type TEXT);
CREATE TABLE loans (loan_id INTEGER PRIMARY KEY, customer_id INTEGER, loan_amount REAL, interest_rate REAL);
CREATE TABLE merchants (merchant_id INTEGER PRIMARY KEY, merchant_name TEXT);
CREATE TABLE branches (branch_id INTEGER PRIMARY KEY, branch_name TEXT, city TEXT);
CREATE TABLE transactions (transaction_id INTEGER PRIMARY KEY, account_id INTEGER, merchant_id INTEGER,
                           amount_usd REAL, transaction_date TEXT);
"""

FIRST = ["Ava", "Liam", "Noah", "Mia", "Zara", "Omar", "Priya", "Lucas", "Emma", "Ethan"]
LAST = ["Smith", "Patel", "Nguyen", "Brown", "Singh", "Garcia", "Chen", "Wilson"]
MERCHANTS = ["FreshMart", "CityFuel", "BookNook", "TechHub", "CafeBrew", "HomeGoods",
             "PharmaPlus", "TravelNow", "StreamFlix", "SportZone", "PetPal", "AutoCare"]


def _day(rng: random.Random, start: date, end: date) -> str:
    return (start + timedelta(days=rng.randrange((end - start).days))).isoformat()


def build_sample_db(path: str | Path = DEFAULT_PATH, seed: int = 7, customers: int = 200) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    rng = random.Random(seed)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    start, end = date(2019, 1, 1), date(2025, 12, 31)
    con.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", [
        (i, rng.choice(FIRST), rng.choice(LAST), rng.randint(450, 850), _day(rng, start, end))
        for i in range(1, customers + 1)
    ])
    accounts = [
        (i, rng.randint(1, customers), rng.choice(["Checking", "Savings", "Business"]),
         round(rng.uniform(50, 60_000), 2), _day(rng, start, end))
        for i in range(1, int(customers * 1.5) + 1)
    ]
    con.executemany("INSERT INTO accounts VALUES (?,?,?,?,?)", accounts)
    con.executemany("INSERT INTO cards VALUES (?,?,?)", [
        (i, rng.randint(1, len(accounts)), rng.choice(["Debit", "Credit", "Prepaid"]))
        for i in range(1, customers * 2 + 1)
    ])
    con.executemany("INSERT INTO loans VALUES (?,?,?,?)", [
        (i, rng.randint(1, customers), round(rng.uniform(1_000, 50_000), 2), round(rng.uniform(3, 15), 2))
        for i in range(1, int(customers * 0.6) + 1)
    ])
    con.executemany("INSERT INTO merchants VALUES (?,?)", list(enumerate(MERCHANTS, start=1)))
    con.executemany("INSERT INTO branches VALUES (?,?,?)", [
        (1, "Downtown", "Toronto"), (2, "Riverside", "Windsor"), (3, "Harbour", "Halifax"),
    ])
    con.executemany("INSERT INTO transactions VALUES (?,?,?,?,?)", [
        (i, rng.randint(1, len(accounts)), rng.randint(1, len(MERCHANTS)),
         round(rng.lognormvariate(3.5, 1.0), 2), _day(rng, start, end))
        for i in range(1, customers * 15 + 1)
    ])
    con.commit()
    con.close()
    return path


if __name__ == "__main__":
    print(f"Sample database written to {build_sample_db()}")
