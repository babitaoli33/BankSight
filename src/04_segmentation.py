import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 110

BASE = "data/raw/banking_dataset_kaggle/data"
con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")
FIG = "figures/"

# Pull one row per customer: credit score, total balance, total loans, txn activity
cust = pd.read_sql("""
    SELECT
        c.customer_id,
        c.credit_score,
        COALESCE(a.total_balance, 0) AS total_balance,
        COALESCE(l.total_loans, 0) AS total_loans
    FROM customers c
    LEFT JOIN (
        SELECT customer_id, SUM(balance_usd) AS total_balance
        FROM accounts GROUP BY customer_id
    ) a ON c.customer_id = a.customer_id
    LEFT JOIN (
        SELECT customer_id, SUM(loan_amount) AS total_loans
        FROM loans GROUP BY customer_id
    ) l ON c.customer_id = l.customer_id
""", con)

# Credit band
def credit_band(score):
    if score < 580: return "Poor"
    elif score < 670: return "Fair"
    elif score < 740: return "Good"
    elif score < 800: return "Very Good"
    else: return "Excellent"

cust['credit_band'] = cust['credit_score'].apply(credit_band)

# Debt-to-balance ratio (loan burden) — avoid divide by zero
cust['debt_to_balance'] = cust['total_loans'] / cust['total_balance'].replace(0, pd.NA)
cust['debt_to_balance'] = cust['debt_to_balance'].fillna(0)

# Simple risk/value segmentation
def segment(row):
    if row['credit_score'] >= 740 and row['debt_to_balance'] < 0.5:
        return "Premium (low risk, high value)"
    elif row['credit_score'] >= 670 and row['debt_to_balance'] < 1.5:
        return "Standard (moderate risk)"
    elif row['debt_to_balance'] >= 1.5:
        return "High Debt Burden (monitor)"
    else:
        return "Subprime (higher risk)"

cust['segment'] = cust.apply(segment, axis=1)

cust.to_csv("data/cleaned/customer_segments.csv", index=False)

print("Segment counts:")
print(cust['segment'].value_counts())
print()
print("Avg metrics by segment:")
print(cust.groupby('segment')[['credit_score', 'total_balance', 'total_loans']].mean().round(0))

# Chart
seg_counts = cust['segment'].value_counts()
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(seg_counts.index, seg_counts.values, color=sns.color_palette("viridis", len(seg_counts)))
ax.set_title("Customer Segments (Credit Score + Debt Burden)")
ax.set_ylabel("Number of Customers")
plt.xticks(rotation=15)
plt.tight_layout()
plt.savefig(FIG + "customer_segments.png")
plt.close()

print("\nSaved: data/cleaned/customer_segments.csv and figures/customer_segments.png")
con.close()