# Microsoft Power BI Integration & Setup Guide

> **Note:** Power BI Desktop is a Windows desktop application. All datasets, DAX measures, Power Query M scripts, and layout specs are provided below. If Power BI Desktop is not installed on the target machine, open the `.csv` exports or connect BigQuery manually in Power BI Desktop to save the `.pbix` file — FinGuard AI does not fabricate `.pbix` binaries.

## 1. Exported Star-Schema Datasets (`powerbi/datasets/`)

Run `GET /api/reports/export?report_type=powerbi_bundle` (or click **Sync Power BI CSV Bundle** on the Reports page) to generate:
- `fact_transactions.csv` — Curated, fraud-scored transactions (masked card tokens)
- `dim_accounts_credit_risk.csv` — Account limits, balances, utilization, delinquency & credit risk tiers
- `dim_customers.csv` — Customer segments, risk categories, home geography
- `dim_merchants.csv` — Merchant categories and risk tiers
- `mart_daily_metrics.csv` — Pre-aggregated daily KPIs
- `fact_quarantined_records.csv` — Rejected records and remediation statuses

## 2. Data Model Relationships

- `dim_customers[customer_id]` (1) ──> (*) `fact_transactions[customer_id]`
- `dim_customers[customer_id]` (1) ──> (*) `dim_accounts_credit_risk[customer_id]`
- `dim_merchants[merchant_id]` (1) ──> (*) `fact_transactions[merchant_id]`
- `fact_quarantined_records` (disconnected governance fact table or linked via `ingestion_job_id`)

## 3. DAX Measures (`powerbi/dax/measures.dax`)

Includes ready-to-paste DAX definitions for:
- `Total Transactions`, `Total Transaction Value`, `Average Transaction Amount`
- `High Risk Transaction Count`, `Suspicious Transaction Rate`, `Flagged Exposure Value`
- `Data Quality Score`, `Validation Failure Rate`, `Duplicate Transaction Rate`
- `Average Credit Utilization`, `Overdue Account Rate`

## 4. Recommended 4-Page Report Layout

1. **Page 1 — Executive Risk Overview**: KPI cards (Total Value, Quality Score, Suspicious Rate, Avg Utilization), Daily Volume & Suspicious Area Chart, Merchant Risk Bar Chart.
2. **Page 2 — Fraud Risk Analysis**: Risk Level Donut, Country Choropleth/Bar, Top Flagged Transactions Table with Explainable Reasons slicer.
3. **Page 3 — Data Quality Monitoring**: Quality Score gauge, Validation Failure & Duplicate Rate KPIs, Quarantined Records breakdown by `failed_rules` and `remediation_status`.
4. **Page 4 — Credit Risk & Governance**: Exposure by Customer Segment, Utilization Distribution Histogram, Overdue Account Rate by Repayment Status.
