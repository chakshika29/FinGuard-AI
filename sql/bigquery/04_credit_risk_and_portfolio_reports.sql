-- ============================================================================
-- FinGuard AI - BigQuery SQL: Credit Risk & Monthly Portfolio Risk Report
-- Business Purpose:
--   Evaluate credit utilization, delinquency exposure by customer segment,
--   and produce monthly executive risk summaries.
-- ============================================================================

-- Query 1: Credit Utilization & Exposure by Segment and Risk Category
SELECT
  c.customer_segment,
  c.customer_risk_category,
  COUNT(DISTINCT a.account_id) AS account_count,
  ROUND(SUM(a.credit_limit), 2) AS total_credit_limit,
  ROUND(SUM(a.outstanding_balance), 2) AS total_exposure,
  ROUND(AVG(a.credit_utilization_ratio) * 100, 2) AS avg_utilization_pct,
  COUNTIF(a.credit_utilization_ratio >= 0.75) AS high_utilization_accounts,
  COUNTIF(a.repayment_status != 'CURRENT') AS overdue_accounts
FROM `finguard_curated.accounts` a
JOIN `finguard_curated.customers` c
  ON a.customer_id = c.customer_id
GROUP BY c.customer_segment, c.customer_risk_category
ORDER BY total_exposure DESC;

-- Query 2: Monthly Portfolio Risk Executive Summary
SELECT
  FORMAT_DATE('%Y-%m', transaction_date) AS billing_month,
  COUNT(*) AS transaction_count,
  ROUND(SUM(transaction_amount), 2) AS gross_dollar_volume,
  COUNT(DISTINCT customer_id) AS active_customers,
  COUNTIF(fraud_risk_level = 'Critical Risk') AS critical_risk_tx,
  COUNTIF(fraud_risk_level = 'High Risk') AS high_risk_tx,
  ROUND(SUM(CASE WHEN fraud_risk_score >= 50 THEN transaction_amount ELSE 0 END), 2) AS flagged_dollar_exposure
FROM `finguard_curated.transactions`
GROUP BY billing_month
ORDER BY billing_month DESC;
