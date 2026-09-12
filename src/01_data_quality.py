import pandas as pd
import sqlite3

BASE = "data/raw/banking_dataset_kaggle/data"
con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")

customers = pd.read_sql("SELECT * FROM customers", con)
accounts = pd.read_sql("SELECT * FROM accounts", con)
cards = pd.read_sql("SELECT * FROM cards", con)
loans = pd.read_sql("SELECT * FROM loans", con)
merchants = pd.read_sql("SELECT * FROM merchants", con)
branches = pd.read_sql("SELECT * FROM branches", con)
transactions = pd.read_sql("SELECT * FROM transactions", con)

tables = {
    "customers": customers, "accounts": accounts, "cards": cards,
    "loans": loans, "merchants": merchants, "branches": branches,
    "transactions": transactions
}

print("=" * 60)
print("SHAPE, NULLS, DUPLICATES")
print("=" * 60)
for name, df in tables.items():
    print(f"\n{name}: {df.shape[0]:,} rows x {df.shape[1]} cols")
    print(f"  Columns: {list(df.columns)}")
    nulls = df.isna().sum().sum()
    dupes = df.duplicated().sum()
    print(f"  Nulls: {nulls} | Duplicate rows: {dupes}")

print("\n" + "=" * 60)
print("REFERENTIAL INTEGRITY CHECKS")
print("=" * 60)

orphan_accounts = ~accounts['customer_id'].isin(customers['customer_id'])
print(f"Accounts with unknown customer_id: {orphan_accounts.sum()}")

orphan_cards = ~cards['account_id'].isin(accounts['account_id'])
print(f"Cards with unknown account_id: {orphan_cards.sum()}")

orphan_loans = ~loans['customer_id'].isin(customers['customer_id'])
print(f"Loans with unknown customer_id: {orphan_loans.sum()}")

orphan_txn_acct = ~transactions['account_id'].isin(accounts['account_id'])
print(f"Transactions with unknown account_id: {orphan_txn_acct.sum()}")

orphan_txn_merch = ~transactions['merchant_id'].isin(merchants['merchant_id'])
print(f"Transactions with unknown merchant_id: {orphan_txn_merch.sum()}")

print("\n" + "=" * 60)
print("VALUE SANITY CHECKS")
print("=" * 60)
print(f"Negative balances: {(accounts['balance_usd'] < 0).sum()}")
print(f"Negative/zero transaction amounts: {(transactions['amount_usd'] <= 0).sum()}")
print(f"Credit score range: {customers['credit_score'].min()} - {customers['credit_score'].max()}")
print(f"Loan amount range: ${loans['loan_amount'].min():,.0f} - ${loans['loan_amount'].max():,.0f}")
print(f"Interest rate range: {loans['interest_rate'].min()}% - {loans['interest_rate'].max()}%")
print(f"Transaction date range: {transactions['transaction_date'].min()} to {transactions['transaction_date'].max()}")
print(f"Account open_date range: {accounts['open_date'].min()} to {accounts['open_date'].max()}")

con.close()