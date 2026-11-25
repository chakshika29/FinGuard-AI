-- ============================================================================
-- FinGuard AI (BigQuery Sandbox) - 04: Customer Spending & Merchant Risk
-- Sandbox Safe: Read-only SELECT, CTEs, GROUP BY, HAVING, and RANK().
-- ============================================================================

-- 1. Top Customer Spending Patterns
SELECT
  customer_id,
  COUNT(*) AS transaction_count,
  ROUND(SUM(transaction_amount), 2) AS total_spend,
  ROUND(AVG(transaction_amount), 2) AS avg_ticket_size,
  ROUND(MAX(transaction_amount), 2) AS max_single_tx,
  COUNT(DISTINCT transaction_country) AS distinct_countries_visited
FROM `finguard_sandbox.cleaned_transactions`
GROUP BY customer_id
HAVING COUNT(*) >= 5
ORDER BY total_spend DESC
LIMIT 50;

-- 2. Merchant Category Risk Analysis with RANK()
SELECT
  merchant_category,
  COUNT(*) AS total_transactions,
  ROUND(SUM(transaction_amount), 2) AS total_volume,
  ROUND(AVG(fraud_risk_score), 2) AS avg_fraud_risk_score,
  COUNTIF(fraud_risk_score >= 50) AS suspicious_tx_count,
  ROUND(100.0 * COUNTIF(fraud_risk_score >= 50) / NULLIF(COUNT(*), 0), 2) AS suspicious_rate_pct,
  RANK() OVER (ORDER BY COUNTIF(fraud_risk_score >= 50) DESC) AS risk_rank
FROM `finguard_sandbox.fraud_analytics`
GROUP BY merchant_category
ORDER BY risk_rank ASC;
