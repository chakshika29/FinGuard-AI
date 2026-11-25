# FinGuard AI Power BI Asset Guide

This folder contains everything required to build the 4-page FinGuard AI Power BI Executive Dashboard:

- `dax/measures.dax`: 17 ready-to-use DAX measures across Transactions, Fraud Risk, Data Quality, and Credit Risk.
- `power_query/finguard_connectors.pq`: Power Query M templates for both **Google BigQuery** and **Local CSV Fallback**.
- `datasets/`: Exported star-schema CSV files (`fact_transactions.csv`, `dim_accounts_credit_risk.csv`, `dim_customers.csv`, `dim_merchants.csv`, `mart_daily_metrics.csv`, `fact_quarantined_records.csv`).

See `docs/POWERBI_SETUP.md` for step-by-step data model relationships and page layout specifications.
