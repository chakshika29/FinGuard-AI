# BigQuery Architecture & Optimization Guide

## 1. 5-Dataset Organization

| Dataset | Purpose | Partitioning & Clustering |
|---|---|---|
| `finguard_raw` | Immutable raw string ingestion | Partitioned by `DATE(loaded_at)` |
| `finguard_staging` | Standardized & validated rows | Partitioned by `DATE(processed_at)`, Clustered by `is_valid, transaction_country` |
| `finguard_curated` | Clean deduplicated ledger + risk scores | Partitioned by `transaction_date`, Clustered by `transaction_country, merchant_category, fraud_risk_level` |
| `finguard_governance` | Quarantined records & audit exports | Partitioned by `DATE(quarantined_at)` |
| `finguard_analytics` | BI views & summary marts | Views over curated tables |

## 2. Cost Control & Dry-Run Estimation

`GCPIntegrationService.estimate_query_cost(sql)` executes `bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)` before running expensive analytics, returning:
- `total_bytes_processed`
- `total_mb_processed`
- `estimated_cost_usd` (at \$6.25/TiB on-demand rate)
- `within_free_tier_1tb` boolean indicator

## 3. Query Optimization Techniques Used in `sql/bigquery/`

1. **Partition Pruning**: Every analytics query filters `WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)` to avoid full-table scans.
2. **Clustering Alignment**: Filtering/grouping by `transaction_country`, `merchant_category`, and `fraud_risk_level` hits clustered storage blocks.
3. **Avoid `SELECT *`**: Analytical queries project only required columns due to BigQuery Capacitor columnar storage.
4. **Windowed Deduplication (`ROW_NUMBER()`) + `MERGE`**: Prevents duplicate records idempotently in a single atomic pass.
