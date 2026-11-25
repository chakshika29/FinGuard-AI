-- ============================================================================
-- FinGuard AI (BigQuery Sandbox) - 03: Data Standardization (CTAS / View)
-- Sandbox Safe: Uses CREATE OR REPLACE TABLE AS SELECT (supported in Sandbox).
-- Demonstrates standardizing inconsistent country names, currencies & types.
-- ============================================================================

CREATE OR REPLACE TABLE `finguard_sandbox.standardized_transactions_demo` AS
SELECT
  TRIM(transaction_id) AS transaction_id,
  TRIM(customer_id) AS customer_id,
  TRIM(account_id) AS account_id,
  SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', transaction_timestamp) AS transaction_timestamp,
  SAFE_CAST(transaction_amount AS FLOAT64) AS transaction_amount,
  UPPER(TRIM(currency)) AS currency,
  TRIM(merchant_id) AS merchant_id,
  UPPER(TRIM(merchant_category)) AS merchant_category,
  CASE UPPER(TRIM(transaction_country))
    WHEN 'USA' THEN 'US'
    WHEN 'UNITED STATES' THEN 'US'
    WHEN 'U.S.' THEN 'US'
    WHEN 'UK' THEN 'GB'
    WHEN 'UNITED KINGDOM' THEN 'GB'
    WHEN 'INDIA' THEN 'IN'
    WHEN 'IND' THEN 'IN'
    ELSE UPPER(TRIM(transaction_country))
  END AS standardized_country,
  UPPER(TRIM(transaction_status)) AS transaction_status
FROM `finguard_sandbox.raw_transactions`
WHERE transaction_id IS NOT NULL
  AND TRIM(transaction_id) != ''
  AND SAFE_CAST(transaction_amount AS FLOAT64) > 0
  AND SAFE.PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%SZ', transaction_timestamp) IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY TRIM(transaction_id) ORDER BY transaction_timestamp ASC) = 1;
