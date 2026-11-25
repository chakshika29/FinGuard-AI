-- ============================================================================
-- FinGuard AI - BigQuery SQL: Fraud Risk, Window Functions & Rolling Averages
-- Business Purpose:
--   Demonstrate LAG/LEAD velocity detection, 7-day rolling averages,
--   merchant risk ranking, and partition-pruned daily transaction trends.
-- ============================================================================

-- Query 1: Daily Transaction Trends with 7-Day Rolling Average (Partition Filtered)
WITH daily_agg AS (
  SELECT
    transaction_date,
    COUNT(*) AS total_transactions,
    ROUND(SUM(transaction_amount), 2) AS daily_volume,
    COUNTIF(fraud_risk_score >= 50) AS suspicious_transactions,
    ROUND(100.0 * COUNTIF(fraud_risk_score >= 50) / NULLIF(COUNT(*), 0), 2) AS suspicious_rate_pct
  FROM `finguard_curated.transactions`
  WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  GROUP BY transaction_date
)
SELECT
  transaction_date,
  total_transactions,
  daily_volume,
  suspicious_transactions,
  suspicious_rate_pct,
  ROUND(AVG(daily_volume) OVER (
    ORDER BY transaction_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ), 2) AS rolling_7d_volume
FROM daily_agg
ORDER BY transaction_date DESC;

-- Query 2: Customer Velocity & Spending Spike Analysis using LAG / LEAD
WITH ordered_tx AS (
  SELECT
    transaction_id,
    customer_id,
    transaction_timestamp,
    transaction_amount,
    transaction_country,
    LAG(transaction_timestamp) OVER (PARTITION BY customer_id ORDER BY transaction_timestamp) AS prev_tx_ts,
    LAG(transaction_country) OVER (PARTITION BY customer_id ORDER BY transaction_timestamp) AS prev_country,
    LEAD(transaction_timestamp) OVER (PARTITION BY customer_id ORDER BY transaction_timestamp) AS next_tx_ts,
    AVG(transaction_amount) OVER (PARTITION BY customer_id) AS customer_avg_amount
  FROM `finguard_curated.transactions`
  WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
)
SELECT
  transaction_id,
  customer_id,
  transaction_timestamp,
  transaction_amount,
  ROUND(customer_avg_amount, 2) AS customer_avg_amount,
  TIMESTAMP_DIFF(transaction_timestamp, prev_tx_ts, SECOND) AS seconds_since_prev_tx,
  CASE
    WHEN TIMESTAMP_DIFF(transaction_timestamp, prev_tx_ts, SECOND) <= 900 THEN 'VELOCITY_BURST'
    WHEN prev_country IS NOT NULL AND transaction_country != prev_country THEN 'GEO_SWITCH'
    WHEN transaction_amount > customer_avg_amount * 3.5 THEN 'AMOUNT_SPIKE'
    ELSE 'NORMAL'
  END AS behavioral_signal
FROM ordered_tx
WHERE TIMESTAMP_DIFF(transaction_timestamp, prev_tx_ts, SECOND) <= 900
   OR (prev_country IS NOT NULL AND transaction_country != prev_country)
   OR transaction_amount > customer_avg_amount * 3.5
ORDER BY transaction_amount DESC
LIMIT 200;

-- Query 3: Merchant Risk Analysis with RANK()
SELECT
  m.merchant_category,
  COUNT(*) AS total_tx,
  ROUND(SUM(t.transaction_amount), 2) AS total_spend,
  ROUND(AVG(t.fraud_risk_score), 2) AS avg_risk_score,
  COUNTIF(t.fraud_risk_score >= 50) AS suspicious_count,
  RANK() OVER (ORDER BY COUNTIF(t.fraud_risk_score >= 50) DESC) AS risk_rank
FROM `finguard_curated.transactions` t
JOIN `finguard_curated.merchants` m
  ON t.merchant_id = m.merchant_id
WHERE t.transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY m.merchant_category
HAVING COUNT(*) >= 10
ORDER BY risk_rank ASC;
