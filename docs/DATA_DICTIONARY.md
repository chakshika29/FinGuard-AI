# FinGuard AI — Enterprise Data Dictionary

> All records are 100% synthetic. No real PII or PCI data is stored.

## 1. Curated Transactions (`finguard_curated.transactions`)

| Column | Type | Nullable | Classification | Description |
|---|---|---|---|---|
| `transaction_id` | STRING | No | Internal | Unique synthetic transaction identifier (`TXN-<seed>-<seq>`). |
| `customer_id` | STRING | No | Restricted | Foreign key to synthetic customer profile (`CUST-xxxxxx`). |
| `account_id` | STRING | No | Restricted | Foreign key to synthetic credit account (`ACCT-xxxxxx`). |
| `card_token` | STRING | Yes | Restricted | Synthetic tokenized card reference; masked as `****xxxx` in UI/exports. |
| `transaction_timestamp` | TIMESTAMP | No | Internal | Standardized UTC event timestamp. |
| `transaction_date` | DATE | No | Internal | BigQuery partition key derived from `transaction_timestamp`. |
| `transaction_amount` | FLOAT64 | No | Confidential | Monetary value (> 0.01 and <= 250,000.00). |
| `currency` | STRING | No | Internal | Validated 3-letter ISO-4217 currency code. |
| `merchant_id` | STRING | No | Internal | Foreign key to merchant directory (`MERCH-xxxxx`). |
| `merchant_category` | STRING | Yes | Internal | Standardized merchant category (e.g., `RETAIL`, `CRYPTO_EXCHANGE`). |
| `transaction_type` | STRING | Yes | Internal | Channel/type (`PURCHASE`, `ONLINE_PAYMENT`, `CONTACTLESS`, etc.). |
| `payment_method` | STRING | Yes | Internal | Instrument (`CREDIT_CARD`, `VIRTUAL_CARD`, `MOBILE_WALLET`, `CHIP_PIN`). |
| `transaction_country` | STRING | Yes | Internal | Standardized 2-letter ISO-3166 country code. |
| `transaction_city` | STRING | Yes | Internal | Standardized title-cased city name. |
| `device_id` | STRING | Yes | Confidential | Synthetic device fingerprint identifier. |
| `transaction_status` | STRING | Yes | Internal | `APPROVED`, `DECLINED`, `PENDING`, `REVERSED`, or `FAILED`. |
| `credit_limit` | FLOAT64 | Yes | Confidential | Account approved credit line. |
| `outstanding_balance` | FLOAT64 | Yes | Confidential | Current unpaid balance on account. |
| `repayment_status` | STRING | Yes | Confidential | `CURRENT`, `PAST_DUE_30`, `PAST_DUE_60`, `PAST_DUE_90`, `DEFAULT`. |
| `customer_risk_category` | STRING | Yes | Confidential | Baseline risk tier (`LOW`, `MEDIUM`, `HIGH`). |
| `fraud_label` | INT64 | Yes | Internal | Synthetic evaluation label (`0` or `1`); **excluded from ML training features**. |
| `fraud_risk_score` | FLOAT64 | No | Confidential | Explainable rule-based risk indicator score (`0.0–100.0`). |
| `fraud_risk_level` | STRING | No | Confidential | `Low Risk`, `Medium Risk`, `High Risk`, `Critical Risk`. |
| `risk_explanations` | STRING | Yes | Confidential | JSON array of human-readable triggered risk indicators. |
| `ml_anomaly_score` | FLOAT64 | Yes | Confidential | Unsupervised IsolationForest anomaly score (`0.0–100.0`). |

## 2. Supporting Tables

- `finguard_curated.customers`: `customer_id`, `full_name_synthetic`, `customer_segment`, `customer_risk_category`, `home_country`, `home_city`, `income_band`, `account_open_date`.
- `finguard_curated.accounts`: `account_id`, `customer_id`, `card_token`, `credit_limit`, `outstanding_balance`, `credit_utilization_ratio`, `repayment_status`, `delinquency_days`, `account_status`, `credit_risk_score`, `credit_risk_tier`.
- `finguard_curated.merchants`: `merchant_id`, `merchant_name`, `merchant_category`, `merchant_country`, `merchant_risk_tier`.
- `finguard_governance.quarantined_records`: `quarantine_id`, `ingestion_job_id`, `transaction_id`, `source_file`, `source_row_number`, `raw_payload`, `failure_reasons`, `failed_rules`, `severity`, `remediation_status`, `remediation_notes`.
