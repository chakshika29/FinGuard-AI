-- ============================================================================
-- FinGuard AI - Local DuckDB Equivalent Analytics Suite
-- Mirrors BigQuery SQL logic using DuckDB-compatible functions (SUM(CASE...),
-- DATE_TRUNC, STRFTIME, EPOCH differences, and CTE windowing).
-- ============================================================================

-- 1. Daily Transaction Trends with 7-Day Rolling Average
WITH daily_agg AS (
  SELECT
    transaction_date,
    COUNT(*) AS total_transactions,
    ROUND(SUM(transaction_amount), 2) AS daily_volume,
    SUM(CASE WHEN fraud_risk_score >= 50 THEN 1 ELSE 0 END) AS suspicious_transactions
  FROM finguard_curated.transactions
  GROUP BY transaction_date
)
SELECT
  transaction_date,
  total_transactions,
  daily_volume,
  suspicious_transactions,
  ROUND(AVG(daily_volume) OVER (
    ORDER BY transaction_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ), 2) AS rolling_7d_volume
FROM daily_agg
ORDER BY transaction_date DESC
LIMIT 30;

-- 2. Customer Velocity & Spending Spike Analysis (DuckDB EPOCH delta)
WITH ordered_tx AS (
  SELECT
    transaction_id,
    customer_id,
    transaction_timestamp,
    transaction_amount,
    LAG(transaction_timestamp) OVER (PARTITION BY customer_id ORDER BY transaction_timestamp) AS prev_tx_ts,
    AVG(transaction_amount) OVER (PARTITION BY customer_id) AS customer_avg_amount
  FROM finguard_curated.transactions
)
SELECT
  transaction_id,
  customer_id,
  transaction_amount,
  ROUND(customer_avg_amount, 2) AS customer_avg_amount,
  EPOCH(transaction_timestamp) - EPOCH(prev_tx_ts) AS seconds_since_prev_tx
FROM ordered_tx
WHERE prev_tx_ts IS NOT NULL
  AND (EPOCH(transaction_timestamp) - EPOCH(prev_tx_ts) <= 900 OR transaction_amount > customer_avg_amount * 3.5)
ORDER BY transaction_amount DESC
LIMIT 50;

-- 3. Monthly Portfolio Risk Summary
SELECT
  STRFTIME(transaction_date, '%Y-%m') AS billing_month,
  COUNT(*) AS transaction_count,
  ROUND(SUM(transaction_amount), 2) AS gross_dollar_volume,
  COUNT(DISTINCT customer_id) AS active_customers,
  SUM(CASE WHEN fraud_risk_level = 'Critical Risk' THEN 1 ELSE 0 END) AS critical_risk_tx,
  SUM(CASE WHEN fraud_risk_level = 'High Risk' THEN 1 ELSE 0 END) AS high_risk_tx
FROM finguard_curated.transactions
GROUP BY billing_month
ORDER BY billing_month DESC;
