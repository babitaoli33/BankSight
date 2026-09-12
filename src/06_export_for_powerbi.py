import pandas as pd
import sqlite3

BASE = "data/raw/banking_dataset_kaggle/data"
con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")

transactions = pd.read_sql("SELECT * FROM transactions", con)
transactions.to_csv("data/cleaned/transactions.csv", index=False)
print(f"Exported {len(transactions):,} transactions to data/cleaned/transactions.csv")

con.close()