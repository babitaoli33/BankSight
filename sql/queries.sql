-- =====================================================
-- BankSight: Retail Banking Customer & Financial Analytics
-- SQL Business Questions
-- =====================================================

-- SECTION 1: DATA QUALITY
-- Business question: Is the data reliable enough to build on?

SELECT COUNT(*) AS orphaned_accounts
FROM accounts a
WHERE NOT EXISTS (SELECT 1 FROM customers c WHERE c.customer_id = a.customer_id);

SELECT COUNT(*) AS orphaned_transactions
FROM transactions t
WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.account_id = t.account_id);


-- SECTION 2: CUSTOMER 360 / PORTFOLIO OVERVIEW
-- Business question: What does the customer base look like at a glance?

SELECT
    COUNT(DISTINCT c.customer_id) AS total_customers,
    COUNT(DISTINCT a.account_id) AS total_accounts,
    ROUND(SUM(a.balance_usd), 2) AS total_balance
FROM customers c
LEFT JOIN accounts a ON c.customer_id = a.customer_id;

-- Business question: How many products does the average customer hold?
SELECT
    a.customer_id,
    COUNT(DISTINCT a.account_id) AS account_count,
    COUNT(DISTINCT cd.card_id) AS card_count,
    COUNT(DISTINCT l.loan_id) AS loan_count
FROM accounts a
LEFT JOIN cards cd ON cd.account_id = a.account_id
LEFT JOIN loans l ON l.customer_id = a.customer_id
GROUP BY a.customer_id
LIMIT 20;


-- SECTION 3: BALANCE & ACCOUNT COMPOSITION
-- Business question: How is total balance distributed across account types?

SELECT
    account_type,
    COUNT(*) AS num_accounts,
    ROUND(AVG(balance_usd), 2) AS avg_balance,
    ROUND(SUM(balance_usd), 2) AS total_balance
FROM accounts
GROUP BY account_type
ORDER BY total_balance DESC;


-- SECTION 4: TRANSACTION ANALYSIS
-- Business question: How has transaction activity trended month over month?

SELECT
    strftime('%Y-%m', transaction_date) AS month,
    COUNT(*) AS num_txns,
    ROUND(SUM(amount_usd), 2) AS total_value
FROM transactions
GROUP BY month
ORDER BY month;

-- Business question: Which merchants generate the most transaction value?
SELECT
    m.merchant_name,
    COUNT(*) AS num_txns,
    ROUND(SUM(t.amount_usd), 2) AS total_value
FROM transactions t
JOIN merchants m ON t.merchant_id = m.merchant_id
GROUP BY m.merchant_name
ORDER BY total_value DESC
LIMIT 10;

-- Business question: Which transactions are unusually large and worth investigating?
-- (Not labeled as fraud. Flagged for further review only.)
SELECT
    t.transaction_id,
    t.account_id,
    t.amount_usd,
    t.transaction_date,
    m.merchant_name
FROM transactions t
JOIN merchants m ON t.merchant_id = m.merchant_id
WHERE t.amount_usd > (
    SELECT amount_usd FROM transactions
    ORDER BY amount_usd DESC
    LIMIT 1 OFFSET (SELECT CAST(COUNT(*) * 0.001 AS INT) FROM transactions)
)
ORDER BY t.amount_usd DESC;


-- SECTION 5: LOANS & CREDIT
-- Business question: How does loan interest rate vary across credit-score bands?

SELECT
    CASE
        WHEN c.credit_score < 580 THEN '1-Poor'
        WHEN c.credit_score < 670 THEN '2-Fair'
        WHEN c.credit_score < 740 THEN '3-Good'
        WHEN c.credit_score < 800 THEN '4-Very Good'
        ELSE '5-Excellent'
    END AS credit_band,
    COUNT(*) AS num_loans,
    ROUND(AVG(l.interest_rate), 3) AS avg_interest_rate,
    ROUND(SUM(l.loan_amount), 2) AS total_loan_value
FROM loans l
JOIN customers c ON l.customer_id = c.customer_id
GROUP BY credit_band
ORDER BY credit_band;


-- SECTION 6: CARDS
-- Business question: What is the card product mix?

SELECT card_type, COUNT(*) AS num_cards
FROM cards
GROUP BY card_type
ORDER BY num_cards DESC;

-- NOTE: branches table intentionally excluded.
-- It has no foreign key relationship to accounts, transactions, or customers
-- in this schema, so it cannot support branch-level performance analysis.