import pandas as pd
import sqlite3

BASE = "data/raw/banking_dataset_kaggle/data"
con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")

customer_360 = pd.read_sql("""
    SELECT
        c.customer_id,
        c.credit_score,
        CASE
            WHEN c.credit_score < 580 THEN '1-Poor'
            WHEN c.credit_score < 670 THEN '2-Fair'
            WHEN c.credit_score < 740 THEN '3-Good'
            WHEN c.credit_score < 800 THEN '4-Very Good'
            ELSE '5-Excellent'
        END AS credit_band,
        COALESCE(acct.account_count, 0) AS account_count,
        COALESCE(acct.total_balance, 0) AS total_balance,
        COALESCE(crd.card_count, 0) AS card_count,
        COALESCE(ln.loan_count, 0) AS loan_count,
        COALESCE(ln.total_loan_value, 0) AS total_loan_value,
        COALESCE(txn.transaction_count, 0) AS transaction_count,
        COALESCE(txn.transaction_value, 0) AS transaction_value
    FROM customers c
    LEFT JOIN (
        SELECT customer_id, COUNT(*) AS account_count, SUM(balance_usd) AS total_balance
        FROM accounts GROUP BY customer_id
    ) acct ON c.customer_id = acct.customer_id
    LEFT JOIN (
        SELECT a.customer_id, COUNT(*) AS card_count
        FROM cards cd JOIN accounts a ON cd.account_id = a.account_id
        GROUP BY a.customer_id
    ) crd ON c.customer_id = crd.customer_id
    LEFT JOIN (
        SELECT customer_id, COUNT(*) AS loan_count, SUM(loan_amount) AS total_loan_value
        FROM loans GROUP BY customer_id
    ) ln ON c.customer_id = ln.customer_id
    LEFT JOIN (
        SELECT a.customer_id, COUNT(*) AS transaction_count, SUM(t.amount_usd) AS transaction_value
        FROM transactions t JOIN accounts a ON t.account_id = a.account_id
        GROUP BY a.customer_id
    ) txn ON c.customer_id = txn.customer_id
""", con)

# product_count = accounts + cards + loans held (simple product adoption measure)
customer_360['product_count'] = (
    (customer_360['account_count'] > 0).astype(int) +
    (customer_360['card_count'] > 0).astype(int) +
    (customer_360['loan_count'] > 0).astype(int)
)

customer_360.to_csv("data/cleaned/customer_360.csv", index=False)

print(f"Customer 360 built: {customer_360.shape[0]:,} rows, {customer_360.shape[1]} columns")
print(customer_360.head())
print()
print(customer_360.describe().round(1))

con.close()