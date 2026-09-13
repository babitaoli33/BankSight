# BankSight: Findings and Business Recommendations

This document summarizes what the analysis found and what a bank could actually do
with each finding. It's written for a non-technical audience, no code or SQL, just
the business story.

---

## The Dataset in Plain Terms

A retail banking dataset covering 50,000 customers, 75,000 accounts, 100,000
cards, 30,000 loans, and 1,000,000 transactions between 2019 and 2025.

To analyze customers properly, every customer's accounts, cards, loans, and
transactions were rolled up into a single Customer 360 view, one row per
customer, showing exactly how many products they hold, how much they've
transacted, and how much they carry in balances and loans. This is the same kind
of table a real bank uses to decide who to cross-sell, who to retain, and who
needs attention.

---

## Finding 1: The data is clean and reliable

Every table checks out, no missing values, no duplicate records, and every
account, card, loan, and transaction correctly links back to a real customer.

**Business meaning:** The bank can trust this data for decision-making without
needing a data cleanup project first.

**Recommendation:** None needed here, this is a green light to build on.

---

## Finding 2: Most customers only hold one or two products

The average customer holds fewer than 2 products (an account, a card, or a
loan) out of 3 possible categories. Very few customers are fully engaged across
all three.

**Business meaning:** There's real room to deepen existing relationships rather
than only chasing new customers. A customer who already trusts the bank with
one account is a natural candidate for a second product.

**Recommendation:** Launch a cross-sell campaign targeted at customers with high
balances but low product counts, they've already shown trust with their money,
they just haven't been offered (or haven't taken) additional products.

---

## Finding 3: Customer value and engagement don't always move together

Customers were grouped into four segments based on how much money they hold
(value) and how connected they are to the bank through products and
transactions (engagement):

| Segment | Customers | What it means |
|---|---|---|
| Loyal High-Value | 20,918 | High balance, actively engaged, the bank's best customers |
| Low-Value, Low-Engagement | 17,888 | Low balance, minimal activity, lowest priority for outreach |
| Engaged Low-Value (Growth Potential) | 7,112 | Active and connected, but hasn't built up balance yet |
| High-Value, Low-Engagement (Cross-Sell Target) | 4,082 | Significant money with the bank, but minimal product usage |

These four segments account for all 50,000 customers, every customer in the
portfolio falls into exactly one group, with no gaps or overlaps.

**Business meaning:** Not every valuable customer is an engaged customer, and
not every engaged customer is valuable yet. Treating all customers the same way
wastes effort on people who won't respond and misses people who would.

**Recommendation:**
- **Loyal High-Value**: protect this relationship, prioritize retention and
  premium service, they are the core of the business.
- **High-Value, Low-Engagement**: the single best cross-sell opportunity in the
  portfolio, they have money and trust but few products.
- **Engaged Low-Value**: nurture toward growth, offer savings or credit-building
  products that match their activity level.
- **Low-Value, Low-Engagement**: lowest priority for active investment, monitor
  but don't over-invest here.

---

## Finding 4: Credit score showed little relationship with loan interest rates in this synthetic dataset

Customers with poor credit scores and customers with excellent credit scores
are paying almost exactly the same average interest rate (about 8.5% either
way).

**Business meaning:** Because the dataset is synthetic, this should not be
interpreted as evidence of an actual lending-pricing issue. In a production
environment, a relationship this flat between credit score and interest rate
would warrant further investigation, real underwriting typically prices risk
into rates with a much wider spread across credit bands.

**Recommendation:** If this pattern appeared in real portfolio data, it would
be an urgent finding for a credit risk team to investigate. For this project,
the takeaway is methodological: always test whether a relationship you'd
expect to see in the data is actually there before building anything on top
of it.

---

## Finding 5: A small number of transactions stand out for their size

About 1,000 transactions (0.1% of all transactions) are unusually large, sitting
just under a $10,000 ceiling. These are not confirmed fraud, they are simply
transactions worth a closer look.

**Business meaning:** Flagging the largest transactions is a reasonable first
screening step, but on its own it isn't precise. Because transaction sizes in
this dataset are spread evenly across the whole range (not clustered around a
typical spending amount, the way real spending usually is), the "largest"
transactions aren't necessarily the most suspicious ones, they're just the
biggest numbers.

**Recommendation:** Use this list as a starting point for manual review, not as
a final answer. In production, a stronger approach compares each transaction
against that specific customer's own typical spending, rather than one global
size cutoff.

---

## Summary

This analysis found that the underlying data is clean and reliable, that most
customers hold only one or two products, and that segmenting customers by
value and engagement (rather than credit risk alone) surfaces a clear
cross-sell opportunity in the "High-Value, Low-Engagement" group. It also
found that credit score does not currently predict loan interest rate, which
would be a serious issue in a real lending portfolio, and that a small number
of unusually large transactions are worth manual review, though they are not
confirmed fraud. Each finding above includes a specific recommendation for
what to do next.

---

## Dashboard Reference

The Power BI dashboard (`BankSight-Dashboard.pbix`) presents these findings
across three pages:
1. **Executive Overview**: portfolio-level KPIs and trends
2. **Customer & Product Analytics**: segments, product adoption, and credit
   distribution
3. **Transactions & Lending**: transaction trends, top merchants, credit band
   vs. interest rate, and unusually large transactions