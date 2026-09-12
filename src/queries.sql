-- 1. Customer growth over time
SELECT strftime('%Y', created_at) AS year, COUNT(*) AS new_customers
FROM customers GROUP BY year ORDER BY year;

-- 2. Balance distribution by account type
SELECT account_type, COUNT(*) AS num_accounts,
       ROUND(AVG(balance_usd),2) AS avg_balance,
       ROUND(SUM(balance_usd),2) AS total_balance
FROM accounts GROUP BY account_type ORDER BY total_balance DESC;

-- 3. Top 10 customers by total account balance
SELECT c.customer_id, c.first_name, c.last_name, SUM(a.balance_usd) AS total_balance
FROM customers c JOIN accounts a ON c.customer_id = a.customer_id
GROUP BY c.customer_id ORDER BY total_balance DESC LIMIT 10;

-- 4. Monthly transaction volume and value
SELECT strftime('%Y-%m', transaction_date) AS month,
       COUNT(*) AS num_txns, ROUND(SUM(amount_usd),2) AS total_value
FROM transactions GROUP BY month ORDER BY month;

-- 5. Top 10 merchants by transaction value
SELECT m.merchant_name, COUNT(*) AS num_txns, ROUND(SUM(t.amount_usd),2) AS total_value
FROM transactions t JOIN merchants m ON t.merchant_id = m.merchant_id
GROUP BY m.merchant_name ORDER BY total_value DESC LIMIT 10;

-- 6. Credit score vs average loan interest rate
SELECT CASE
         WHEN c.credit_score < 580 THEN 'Poor (<580)'
         WHEN c.credit_score < 670 THEN 'Fair (580-669)'
         WHEN c.credit_score < 740 THEN 'Good (670-739)'
         WHEN c.credit_score < 800 THEN 'Very Good (740-799)'
         ELSE 'Excellent (800+)'
       END AS credit_band,
       COUNT(*) AS num_loans, ROUND(AVG(l.interest_rate),2) AS avg_interest_rate
FROM loans l JOIN customers c ON l.customer_id = c.customer_id
GROUP BY credit_band ORDER BY avg_interest_rate DESC;

-- 7. Card type mix
SELECT card_type, COUNT(*) AS num_cards
FROM cards GROUP BY card_type ORDER BY num_cards DESC;

-- 8. Cards expiring in the next 12 months (renewal risk)
SELECT COUNT(*) AS expiring_soon
FROM cards WHERE expiration_date <= date('now', '+12 months');

-- 9. Customers with no accounts (should be 0 given integrity checks, sanity confirm)
SELECT COUNT(*) FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM accounts a WHERE a.customer_id = c.customer_id);

-- 10. Loan burden per customer (total loans vs total balance)
SELECT c.customer_id,
       ROUND(SUM(DISTINCT a.balance_usd),2) AS total_balance,
       ROUND(SUM(DISTINCT l.loan_amount),2) AS total_loans
FROM customers c
LEFT JOIN accounts a ON c.customer_id = a.customer_id
LEFT JOIN loans l ON c.customer_id = l.customer_id
GROUP BY c.customer_id
HAVING total_loans > total_balance
ORDER BY total_loans DESC LIMIT 10;