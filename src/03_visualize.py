import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 110

BASE = "data/raw/banking_dataset_kaggle/data"
con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")
FIG = "figures/"

# 1. Monthly transaction value trend
monthly = pd.read_sql("""
    SELECT strftime('%Y-%m', transaction_date) AS month,
           COUNT(*) AS num_txns, SUM(amount_usd) AS total_value
    FROM transactions GROUP BY month ORDER BY month
""", con)
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(monthly['month'], monthly['total_value'], color="#065A82", linewidth=1.5)
ax.set_title("Monthly Transaction Value (2019-2025)")
ax.set_ylabel("Total Value ($)")
ax.set_xticks(ax.get_xticks()[::6])
plt.xticks(rotation=90)
plt.tight_layout()
plt.savefig(FIG + "monthly_txn_value.png")
plt.close()

# 2. Balance by account type
bal = pd.read_sql("""
    SELECT account_type, AVG(balance_usd) AS avg_balance, SUM(balance_usd) AS total_balance
    FROM accounts GROUP BY account_type
""", con)
fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(bal['account_type'], bal['total_balance'], color=["#065A82", "#1C7293", "#21295C"])
ax.set_title("Total Balance by Account Type")
ax.set_ylabel("Total Balance ($)")
plt.tight_layout()
plt.savefig(FIG + "balance_by_type.png")
plt.close()

# 3. Credit score distribution
credit = pd.read_sql("SELECT credit_score FROM customers", con)
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(credit['credit_score'], bins=30, color="#1C7293", edgecolor="white")
ax.set_title("Customer Credit Score Distribution")
ax.set_xlabel("Credit Score")
plt.tight_layout()
plt.savefig(FIG + "credit_score_dist.png")
plt.close()

# 4. Credit band vs avg interest rate
ci = pd.read_sql("""
    SELECT CASE
             WHEN c.credit_score < 580 THEN '1-Poor'
             WHEN c.credit_score < 670 THEN '2-Fair'
             WHEN c.credit_score < 740 THEN '3-Good'
             WHEN c.credit_score < 800 THEN '4-Very Good'
             ELSE '5-Excellent'
           END AS credit_band,
           AVG(l.interest_rate) AS avg_rate
    FROM loans l JOIN customers c ON l.customer_id = c.customer_id
    GROUP BY credit_band ORDER BY credit_band
""", con)
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(ci['credit_band'], ci['avg_rate'], color="#F96167")
ax.set_ylim(0, 10)
ax.set_title("Avg Loan Interest Rate by Credit Band\n(Notably flat — rates appear independent of credit score)")
ax.set_ylabel("Avg Interest Rate (%)")
plt.tight_layout()
plt.savefig(FIG + "credit_vs_interest.png")
plt.close()

# 5. Top 10 merchants
merch = pd.read_sql("""
    SELECT m.merchant_name, SUM(t.amount_usd) AS total_value
    FROM transactions t JOIN merchants m ON t.merchant_id = m.merchant_id
    GROUP BY m.merchant_name ORDER BY total_value DESC LIMIT 10
""", con)
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(merch['merchant_name'][::-1], merch['total_value'][::-1], color="#028090")
ax.set_title("Top 10 Merchants by Transaction Value")
ax.set_xlabel("Total Value ($)")
plt.tight_layout()
plt.savefig(FIG + "top_merchants.png")
plt.close()

print("5 charts saved to figures/")
con.close()