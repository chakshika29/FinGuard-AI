-- ============================================================================
-- FinGuard AI - BigQuery Enterprise Warehouse DDL (5-Layer Architecture)
-- Note: All financial records are 100% synthetic.
-- ============================================================================

-- 1. Create Datasets (Schemas)
CREATE SCHEMA IF NOT EXISTS `finguard_raw`;
CREATE SCHEMA IF NOT EXISTS `finguard_staging`;
CREATE SCHEMA IF NOT EXISTS `finguard_curated`;
CREATE SCHEMA IF NOT EXISTS `finguard_governance`;
CREATE SCHEMA IF NOT EXISTS `finguard_analytics`;

-- 2. Raw Landing Table (unparsed strings to preserve malformed inputs)
CREATE TABLE IF NOT EXISTS `finguard_raw.transactions_raw` (
  transaction_id STRING,
  customer_id STRING,
  account_id STRING,
  card_token STRING,
  transaction_timestamp STRING,
  transaction_amount STRING,
  currency STRING,
  merchant_id STRING,
  merchant_category STRING,
  transaction_type STRING,
  payment_method STRING,
  transaction_country STRING,
  transaction_city STRING,
  device_id STRING,
  transaction_status STRING,
  credit_limit STRING,
  outstanding_balance STRING,
  repayment_status STRING,
  customer_risk_category STRING,
  fraud_label STRING,
  ingestion_timestamp STRING,
  source_system STRING,
  ingestion_job_id STRING NOT NULL,
  file_checksum STRING NOT NULL,
  source_file STRING,
  source_row_number INT64,
  loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(loaded_at);

-- 3. Staging Table (standardized types + validation flags)
CREATE TABLE IF NOT EXISTS `finguard_staging.transactions_staging` (
  transaction_id STRING,
  customer_id STRING,
  account_id STRING,
  card_token STRING,
  transaction_timestamp TIMESTAMP,
  transaction_amount FLOAT64,
  currency STRING,
  merchant_id STRING,
  merchant_category STRING,
  transaction_type STRING,
  payment_method STRING,
  transaction_country STRING,
  transaction_city STRING,
  device_id STRING,
  transaction_status STRING,
  credit_limit FLOAT64,
  outstanding_balance FLOAT64,
  repayment_status STRING,
  customer_risk_category STRING,
  fraud_label INT64,
  ingestion_timestamp TIMESTAMP,
  source_system STRING,
  ingestion_job_id STRING,
  is_valid BOOL,
  validation_errors STRING,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(processed_at)
CLUSTER BY is_valid, transaction_country;

-- 4. Curated Transactions Table (Partitioned by transaction_date, Clustered for BI)
CREATE TABLE IF NOT EXISTS `finguard_curated.transactions` (
  transaction_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  account_id STRING NOT NULL,
  card_token STRING,
  transaction_timestamp TIMESTAMP NOT NULL,
  transaction_date DATE NOT NULL,
  transaction_amount FLOAT64 NOT NULL,
  currency STRING NOT NULL,
  merchant_id STRING NOT NULL,
  merchant_category STRING,
  transaction_type STRING,
  payment_method STRING,
  transaction_country STRING,
  transaction_city STRING,
  device_id STRING,
  transaction_status STRING,
  credit_limit FLOAT64,
  outstanding_balance FLOAT64,
  repayment_status STRING,
  customer_risk_category STRING,
  fraud_label INT64,
  ingestion_timestamp TIMESTAMP,
  source_system STRING,
  ingestion_job_id STRING,
  fraud_risk_score FLOAT64,
  fraud_risk_level STRING,
  risk_explanations STRING,
  ml_anomaly_score FLOAT64
)
PARTITION BY transaction_date
CLUSTER BY transaction_country, merchant_category, fraud_risk_level;

CREATE TABLE IF NOT EXISTS `finguard_curated.customers` (
  customer_id STRING NOT NULL,
  full_name_synthetic STRING,
  customer_segment STRING,
  customer_risk_category STRING,
  home_country STRING,
  home_city STRING,
  income_band STRING,
  account_open_date DATE,
  updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `finguard_curated.accounts` (
  account_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  card_token STRING,
  credit_limit FLOAT64,
  outstanding_balance FLOAT64,
  credit_utilization_ratio FLOAT64,
  repayment_status STRING,
  delinquency_days INT64,
  account_status STRING,
  credit_risk_score FLOAT64,
  credit_risk_tier STRING,
  updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `finguard_curated.merchants` (
  merchant_id STRING NOT NULL,
  merchant_name STRING,
  merchant_category STRING,
  merchant_country STRING,
  merchant_risk_tier STRING,
  updated_at TIMESTAMP
);

-- 5. Governance Quarantine Table
CREATE TABLE IF NOT EXISTS `finguard_governance.quarantined_records` (
  quarantine_id STRING NOT NULL,
  ingestion_job_id STRING NOT NULL,
  transaction_id STRING,
  source_file STRING,
  source_row_number INT64,
  raw_payload STRING,
  failure_reasons STRING NOT NULL,
  failed_rules STRING,
  severity STRING,
  remediation_status STRING,
  remediation_notes STRING,
  quarantined_at TIMESTAMP,
  updated_at TIMESTAMP
)
PARTITION BY DATE(quarantined_at);

-- 6. Analytics Views for Power BI & Executive Reporting
CREATE OR REPLACE VIEW `finguard_analytics.v_executive_transactions` AS
SELECT
  t.transaction_id,
  t.customer_id,
  t.account_id,
  CONCAT('****', RIGHT(COALESCE(t.card_token, '0000'), 4)) AS card_token_masked,
  t.transaction_timestamp,
  t.transaction_date,
  t.transaction_amount,
  t.currency,
  t.merchant_id,
  t.merchant_category,
  t.transaction_country,
  t.transaction_status,
  t.fraud_risk_score,
  t.fraud_risk_level,
  c.customer_segment,
  m.merchant_risk_tier
FROM `finguard_curated.transactions` t
LEFT JOIN `finguard_curated.customers` c ON t.customer_id = c.customer_id
LEFT JOIN `finguard_curated.merchants` m ON t.merchant_id = m.merchant_id;
