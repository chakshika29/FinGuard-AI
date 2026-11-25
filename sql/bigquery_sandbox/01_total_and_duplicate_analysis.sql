-- ============================================================================
-- FinGuard AI (BigQuery Sandbox) - 01: Total Transaction & Duplicate Detection
-- Sandbox Safe: Uses SELECT and CTEs only (no MERGE, UPDATE, or DELETE).
-- Dataset assumed: finguard_sandbox (replace if you used another dataset name).
-- ============================================================================

-- 1. Total Transaction Portfolio Summary (Cleaned Curated Table)
SELECT
  COUNT(*) AS total_transactions,
  COUNT(DISTINCT customer_id) AS unique_customers,
  COUNT(DISTINCT merchant_id) AS unique_merchants,
  ROUND(SUM(transaction_amount), 2) AS total_transaction_value,
  ROUND(AVG(transaction_amount), 2) AS avg_transaction_amount,
  ROUND(MIN(transaction_amount), 2) AS min_amount,
  ROUND(MAX(transaction_amount), 2) AS max_amount
FROM `finguard_sandbox.cleaned_transactions`;

-- 2. Duplicate Transaction Detection on Raw Table (GROUP BY + HAVING + Window)
WITH duplicate_candidates AS (
  SELECT
    transaction_id,
    COUNT(*) AS occurrence_count,
    MIN(transaction_timestamp) AS first_timestamp,
    MAX(transaction_timestamp) AS last_timestamp
  FROM `finguard_sandbox.raw_transactions`
  WHERE transaction_id IS NOT NULL
    AND TRIM(transaction_id) != ''
  GROUP BY transaction_id
  HAVING COUNT(*) > 1
)
SELECT
  transaction_id,
  occurrence_count,
  first_timestamp,
  last_timestamp
FROM duplicate_candidates
ORDER BY occurrence_count DESC, transaction_id
LIMIT 100;
