-- ============================================================================
-- FinGuard AI (BigQuery Sandbox) - 05: Suspicious Transactions, Fraud Dist & Windows
-- Sandbox Safe: Demonstrates LAG, LEAD, rolling averages, and risk segmentation.
-- Note: Suspicious flags are risk indicators, NOT confirmed fraud.
-- ============================================================================

-- 1. Fraud Risk Severity Distribution
SELECT
  fraud_risk_level,
  COUNT(*) AS transaction_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_portfolio,
  ROUND(SUM(transaction_amount), 2) AS total_dollar_volume,
  ROUND(AVG(fraud_risk_score), 2) AS avg_risk_score
FROM `finguard_sandbox.fraud_analytics`
GROUP BY fraud_risk_level
ORDER BY avg_risk_score DESC;

-- 2. Suspicious Transaction Detection (High & Critical Risk Indicators)
SELECT
  transaction_id,
  customer_id,
  merchant_category,
  transaction_country,
  transaction_amount,
  fraud_risk_score,
  fraud_risk_level,
  risk_explanations
FROM `finguard_sandbox.fraud_analytics`
WHERE fraud_risk_score >= 50
ORDER BY fraud_risk_score DESC, transaction_amount DESC
LIMIT 100;

-- 3. Window Functions: LAG / LEAD Velocity & 7-Day Rolling Volume
WITH daily_volume AS (
  SELECT
    DATE(transaction_date) AS tx_date,
    COUNT(*) AS tx_count,
    ROUND(SUM(transaction_amount), 2) AS daily_spend
  FROM `finguard_sandbox.cleaned_transactions`
  GROUP BY tx_date
)
SELECT
  tx_date,
  tx_count,
  daily_spend,
  LAG(daily_spend) OVER (ORDER BY tx_date) AS prev_day_spend,
  LEAD(daily_spend) OVER (ORDER BY tx_date) AS next_day_spend,
  ROUND(AVG(daily_spend) OVER (
    ORDER BY tx_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ), 2) AS rolling_7d_avg_spend
FROM daily_volume
ORDER BY tx_date DESC
LIMIT 30;
