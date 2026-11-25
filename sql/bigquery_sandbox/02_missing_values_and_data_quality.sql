-- ============================================================================
-- FinGuard AI (BigQuery Sandbox) - 02: Missing Value & Data Quality Assessment
-- Sandbox Safe: Read-only SELECT and CTE analytics (zero DML).
-- ============================================================================

-- 1. Missing Mandatory Values & Type Anomaly Check on Raw Transactions
SELECT
  COUNT(*) AS total_raw_records,
  COUNTIF(transaction_id IS NULL OR TRIM(transaction_id) = '') AS missing_transaction_id,
  COUNTIF(customer_id IS NULL OR TRIM(customer_id) = '') AS missing_customer_id,
  COUNTIF(merchant_id IS NULL OR TRIM(merchant_id) = '') AS missing_merchant_id,
  COUNTIF(SAFE_CAST(transaction_amount AS FLOAT64) IS NULL) AS non_numeric_amount,
  COUNTIF(SAFE_CAST(transaction_amount AS FLOAT64) <= 0) AS non_positive_amount,
  COUNTIF(SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', transaction_timestamp) IS NULL) AS invalid_timestamp_format,
  COUNTIF(UPPER(TRIM(currency)) NOT IN ('USD', 'EUR', 'GBP', 'CAD', 'INR', 'SGD', 'AUD', 'JPY')) AS invalid_currency_code
FROM `finguard_sandbox.raw_transactions`;

-- 2. Overall Data Quality Assessment Score (Cleaned vs. Quarantined)
WITH counts AS (
  SELECT
    (SELECT COUNT(*) FROM `finguard_sandbox.cleaned_transactions`) AS valid_count,
    (SELECT COUNT(*) FROM `finguard_sandbox.quarantined_records`) AS quarantined_count
)
SELECT
  valid_count,
  quarantined_count,
  valid_count + quarantined_count AS total_evaluated,
  ROUND(100.0 * valid_count / NULLIF(valid_count + quarantined_count, 0), 2) AS overall_pass_rate_pct
FROM counts;
