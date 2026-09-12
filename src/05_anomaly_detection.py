import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 110

BASE = "data/raw/banking_dataset_kaggle/data"
con = sqlite3.connect(f"{BASE}/database/bank_sqlite.db")
FIG = "figures/"

# Check the actual shape of the distribution first
shape = pd.read_sql("""
    SELECT MIN(amount_usd) AS min_amt, MAX(amount_usd) AS max_amt,
           AVG(amount_usd) AS mean_amt
    FROM transactions
""", con)
print("Distribution shape:")
print(shape.to_string(index=False))

# Percentile-based thresholds (robust to any distribution shape)
pctl = pd.read_sql("SELECT amount_usd FROM transactions", con)
p99 = pctl['amount_usd'].quantile(0.99)
p999 = pctl['amount_usd'].quantile(0.999)

print(f"\n99th percentile: ${p99:,.2f}")
print(f"99.9th percentile: ${p999:,.2f}")

# Flag top 0.1% as "unusual" (a common real-world fraud-screening cutoff)
flagged = pd.read_sql(f"""
    SELECT t.transaction_id, t.account_id, t.amount_usd, t.transaction_date, m.merchant_name
    FROM transactions t
    JOIN merchants m ON t.merchant_id = m.merchant_id
    WHERE t.amount_usd > {p999}
    ORDER BY t.amount_usd DESC
""", con)

print(f"\nFlagged transactions (top 0.1%): {len(flagged):,} out of 1,000,000")
print("\nTop 10 largest flagged:")
print(flagged.head(10).to_string(index=False))

flagged.to_csv("data/cleaned/flagged_transactions.csv", index=False)

# Distribution chart with percentile threshold line
sample = pd.read_sql("SELECT amount_usd FROM transactions ORDER BY RANDOM() LIMIT 50000", con)
fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(sample['amount_usd'], bins=60, color="#1C7293", edgecolor="white")
ax.axvline(p999, color="#F96167", linestyle="--", linewidth=2, label=f"99.9th percentile (${p999:,.0f})")
ax.set_title("Transaction Amount Distribution with Anomaly Threshold")
ax.set_xlabel("Transaction Amount ($)")
ax.legend()
plt.tight_layout()
plt.savefig(FIG + "anomaly_threshold.png")
plt.close()

print("\nSaved: data/cleaned/flagged_transactions.csv and figures/anomaly_threshold.png")
con.close()