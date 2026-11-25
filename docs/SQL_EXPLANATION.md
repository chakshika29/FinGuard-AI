# SQL Architecture & Query Business Purposes

## 1. BigQuery Sandbox SQL Suite (`sql/bigquery_sandbox/`)

All queries in `sql/bigquery_sandbox/` are **100% BigQuery Sandbox compatible** (no billing, no DML `MERGE`/`UPDATE`/`DELETE`):

| Script | SQL Techniques | Business Purpose |
|---|---|---|
| `01_total_and_duplicate_analysis.sql` | `COUNT`, `SUM`, `AVG`, `GROUP BY`, `HAVING`, CTEs | Calculate portfolio transaction totals and isolate duplicate `transaction_id` values in `raw_transactions`. |
| `02_missing_values_and_data_quality.sql` | `COUNTIF`, `SAFE_CAST`, `SAFE.PARSE_TIMESTAMP`, CTEs | Measure missing mandatory fields, invalid types/timestamps/currencies, and overall dataset pass rate. |
| `03_data_standardization_ctas.sql` | `CREATE OR REPLACE TABLE ... AS SELECT`, `CASE`, `QUALIFY ROW_NUMBER()` | Demonstrate zero-DML standardization of country variants (`USA`→`US`, `United Kingdom`→`GB`) and deduplication. |
| `04_customer_and_merchant_risk.sql` | `GROUP BY`, `HAVING`, `COUNTIF`, `RANK() OVER` | Identify top spending customer cohorts and rank merchant categories by suspicious transaction rate. |
| `05_fraud_and_window_functions.sql` | `SUM() OVER`, `LAG`, `LEAD`, `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` | Monitor fraud severity distribution, high/critical alerts, day-over-day spend shifts, and 7-day rolling averages. |
| `06_credit_utilization_and_governance.sql` | `GROUP BY`, `AVG`, `COUNTIF` | Track segment-level credit utilization, delinquency exposure, and quarantine remediation backlog. |

### Verified Live BigQuery Sandbox Run (`finguard-ai-515807`)
- Queried `finguard_analytics.raw_transactions` (**120,000** uploaded synthetic records).
- Verified **10** distinct merchant categories returned with **2.34 MB** estimated query scan on merchant analytics.

## 2. Local DuckDB & Enterprise BigQuery Reference Scripts
- `sql/local/duckdb_analytics_suite.sql`: Local DuckDB equivalents (`SUM(CASE WHEN ...)`, `EPOCH()`, `STRFTIME()`).
- `sql/bigquery/` & `sql/schemas/bigquery_ddl.sql`: Reference DDL/DML scripts (partitioning, clustering, `MERGE`) for paid BigQuery environments.
