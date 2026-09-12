import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams['figure.dpi'] = 110

cust = pd.read_csv("data/cleaned/customer_360.csv")

# Engagement score: combine product count and transaction activity
cust['engagement_score'] = cust['product_count'] + (cust['transaction_count'] > cust['transaction_count'].median()).astype(int)

balance_median = cust['total_balance'].median()
engagement_median = cust['engagement_score'].median()

def value_engagement_segment(row):
    high_value = row['total_balance'] >= balance_median
    high_engagement = row['engagement_score'] >= engagement_median
    if high_value and high_engagement:
        return 'Loyal High-Value'
    elif high_value and not high_engagement:
        return 'High-Value, Low-Engagement (Cross-Sell Target)'
    elif not high_value and high_engagement:
        return 'Engaged Low-Value (Growth Potential)'
    else:
        return 'Low-Value, Low-Engagement'

cust['customer_segment'] = cust.apply(value_engagement_segment, axis=1)
cust.to_csv("data/cleaned/customer_360.csv", index=False)

seg_summary = cust.groupby('customer_segment').agg(
    customers=('customer_id', 'count'),
    avg_balance=('total_balance', 'mean'),
    avg_product_count=('product_count', 'mean'),
    avg_transaction_value=('transaction_value', 'mean')
).round(0)

print(seg_summary)

fig, ax = plt.subplots(figsize=(10, 6))
seg_counts = cust['customer_segment'].value_counts()
ax.bar(seg_counts.index, seg_counts.values, color=sns.color_palette('viridis', len(seg_counts)))
ax.set_title('Customer Value & Engagement Segments')
ax.set_ylabel('Number of Customers')
plt.xticks(rotation=15, ha='right')
plt.tight_layout()
plt.savefig("figures/customer_value_segments.png")
plt.close()

print("\nSaved: data/cleaned/customer_360.csv (updated) and figures/customer_value_segments.png")