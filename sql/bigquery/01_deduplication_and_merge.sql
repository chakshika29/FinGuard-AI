-- ============================================================================
-- FinGuard AI - BigQuery SQL: Deduplication, Window Ranking & Idempotent MERGE
-- Business Purpose:
--   1. Detect duplicate transaction_ids arriving in staging batches.
--   2. Deduplicate using ROW_NUMBER() keeping the earliest valid payload.
--   3. Idempotently MERGE clean records into partitioned finguard_curated.transactions.
-- ============================================================================

-- Query 1: Duplicate Transaction Detection using GROUP BY + HAVING + Window Count
WITH staged_ranked AS (
  SELECT
    transaction_id,
    customer_id,
    transaction_amount,
    ingestion_job_id,
    processed_at,
    COUNT(*) OVER (PARTITION BY transaction_id) AS occurrence_count,
    ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY processed_at ASC) AS row_rank
  FROM `finguard_staging.transactions_staging`
  WHERE transaction_id IS NOT NULL AND TRIM(transaction_id) != ''
)
SELECT
  transaction_id,
  occurrence_count,
  MIN(processed_at) AS first_seen_at,
  MAX(processed_at) AS last_seen_at
FROM staged_ranked
WHERE occurrence_count > 1
GROUP BY transaction_id, occurrence_count
ORDER BY occurrence_count DESC;

-- Query 2: Idempotent MERGE into Curated Partitioned Table
MERGE `finguard_curated.transactions` AS target
USING (
  SELECT
    transaction_id,
    customer_id,
    account_id,
    card_token,
    transaction_timestamp,
    DATE(transaction_timestamp) AS transaction_date,
    transaction_amount,
    currency,
    merchant_id,
    merchant_category,
    transaction_type,
    payment_method,
    transaction_country,
    transaction_city,
    device_id,
    transaction_status,
    credit_limit,
    outstanding_balance,
    repayment_status,
    customer_risk_category,
    fraud_label,
    ingestion_timestamp,
    source_system,
    ingestion_job_id,
    0.0 AS fraud_risk_score,
    'Low Risk' AS fraud_risk_level,
    '[]' AS risk_explanations,
    0.0 AS ml_anomaly_score
  FROM (
    SELECT *,
      ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY processed_at ASC) AS rn
    FROM `finguard_staging.transactions_staging`
    WHERE is_valid = TRUE
  )
  WHERE rn = 1
) AS src
ON target.transaction_id = src.transaction_id
WHEN NOT MATCHED THEN
  INSERT ROW;
