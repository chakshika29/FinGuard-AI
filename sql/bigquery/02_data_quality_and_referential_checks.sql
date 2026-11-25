-- ============================================================================
-- FinGuard AI - BigQuery SQL: Data Quality, Referential Integrity & Freshness
-- Business Purpose:
--   Compute transparent 7-dimension quality metrics, detect missing values,
--   identify orphan customer/merchant references, and monitor SLA freshness.
-- ============================================================================

-- Query 1: Missing Value & Conditional Aggregation Analysis
SELECT
  COUNT(*) AS total_staged_rows,
  COUNTIF(transaction_id IS NULL OR TRIM(transaction_id) = '') AS missing_transaction_id,
  COUNTIF(customer_id IS NULL OR TRIM(customer_id) = '') AS missing_customer_id,
  COUNTIF(transaction_amount IS NULL OR transaction_amount <= 0) AS invalid_amount_count,
  COUNTIF(transaction_timestamp IS NULL) AS invalid_timestamp_count,
  ROUND(100.0 * COUNTIF(is_valid = TRUE) / NULLIF(COUNT(*), 0), 2) AS batch_valid_pct
FROM `finguard_staging.transactions_staging`;

-- Query 2: Referential Integrity Check (Orphan Customers & Merchants)
SELECT
  'CUSTOMER_ORPHAN' AS violation_type,
  s.transaction_id,
  s.customer_id AS missing_reference_key
FROM `finguard_staging.transactions_staging` s
LEFT JOIN `finguard_curated.customers` c
  ON s.customer_id = c.customer_id
WHERE s.customer_id IS NOT NULL
  AND TRIM(s.customer_id) != ''
  AND c.customer_id IS NULL
UNION ALL
SELECT
  'MERCHANT_ORPHAN' AS violation_type,
  s.transaction_id,
  s.merchant_id AS missing_reference_key
FROM `finguard_staging.transactions_staging` s
LEFT JOIN `finguard_curated.merchants` m
  ON s.merchant_id = m.merchant_id
WHERE s.merchant_id IS NOT NULL
  AND TRIM(s.merchant_id) != ''
  AND m.merchant_id IS NULL;

-- Query 3: Data Freshness & Governance Policy Violation Monitoring
WITH freshness AS (
  SELECT
    MAX(transaction_timestamp) AS latest_event_ts,
    MAX(ingestion_timestamp) AS latest_ingestion_ts,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(ingestion_timestamp), HOUR) AS ingestion_lag_hours
  FROM `finguard_curated.transactions`
  WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
)
SELECT
  latest_event_ts,
  latest_ingestion_ts,
  ingestion_lag_hours,
  CASE
    WHEN ingestion_lag_hours > 24 THEN 'POLICY_VIOLATION: POL-006 Freshness SLA Breached'
    ELSE 'COMPLIANT'
  END AS freshness_policy_status
FROM freshness;
