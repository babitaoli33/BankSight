import pandas as pd
import sqlite3

BASE = "data/raw/banking_dataset_kaggle/data"
con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")

queries = {
    "customer_growth": """
        SELECT strftime('%Y', created_at) AS year, COUNT(*) AS new_customers
        FROM customers GROUP BY year ORDER BY year
    """,
    "balance_by_type": """
        SELECT account_type, COUNT(*) AS num_accounts,
               ROUND(AVG(balance_usd),2) AS avg_balance,
               ROUND(SUM(balance_usd),2) AS total_balance
        FROM accounts GROUP BY account_type ORDER BY total_balance DESC
    """,
    "top_customers": """
        SELECT c.customer_id, c.first_name, c.last_name, SUM(a.balance_usd) AS total_balance
        FROM customers c JOIN accounts a ON c.customer_id = a.customer_id
        GROUP BY c.customer_id ORDER BY total_balance DESC LIMIT 10
    """,
    "monthly_txns": """
        SELECT strftime('%Y-%m', transaction_date) AS month,
               COUNT(*) AS num_txns, ROUND(SUM(amount_usd),2) AS total_value
        FROM transactions GROUP BY month ORDER BY month
    """,
    "top_merchants": """
        SELECT m.merchant_name, COUNT(*) AS num_txns, ROUND(SUM(t.amount_usd),2) AS total_value
        FROM transactions t JOIN merchants m ON t.merchant_id = m.merchant_id
        GROUP BY m.merchant_name ORDER BY total_value DESC LIMIT 10
    """,
    "credit_vs_interest": """
        SELECT CASE
                 WHEN c.credit_score < 580 THEN 'Poor (<580)'
                 WHEN c.credit_score < 670 THEN 'Fair (580-669)'
                 WHEN c.credit_score < 740 THEN 'Good (670-739)'
                 WHEN c.credit_score < 800 THEN 'Very Good (740-799)'
                 ELSE 'Excellent (800+)'
               END AS credit_band,
               COUNT(*) AS num_loans, ROUND(AVG(l.interest_rate),2) AS avg_interest_rate
        FROM loans l JOIN customers c ON l.customer_id = c.customer_id
        GROUP BY credit_band ORDER BY avg_interest_rate DESC
    """,
    "card_mix": """
        SELECT card_type, COUNT(*) AS num_cards
        FROM cards GROUP BY card_type ORDER BY num_cards DESC
    """,
}

for name, sql in queries.items():
    print("=" * 60)
    print(name.upper())
    print("=" * 60)
    df = pd.read_sql(sql, con)
    print(df.to_string(index=False))
    print()

con.close()