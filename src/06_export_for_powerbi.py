import pandas as pd
import sqlite3

BASE = "data/raw/banking_dataset_kaggle/data"
con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")

transactions = pd.read_sql("""
    SELECT
        t.transaction_id,
        t.account_id,
        t.merchant_id,
        m.merchant_name,
        t.amount_usd,
        t.transaction_date
    FROM transactions t
    JOIN merchants m ON t.merchant_id = m.merchant_id
""", con)

transactions.to_csv("data/cleaned/transactions.csv", index=False)
print(f"Exported {len(transactions):,} transactions with merchant_name pre-joined")

con.close()