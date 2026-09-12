import pandas as pd
import sqlite3

BASE = "data/raw/banking_dataset_kaggle/data"

con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con)
print("Tables found:", tables['name'].tolist())

df = pd.read_csv(f"{BASE}/csv/customers.csv")
print("Customers loaded:", df.shape)
con.close()