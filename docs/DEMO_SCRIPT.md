# FinGuard AI — 3-Minute Project Demo & Interview Script
*(Aligned with American Express Analyst – Data Governance & Management)*

## 3-Minute Live Walkthrough

- **0:00 – 0:35 | Business Problem & Architecture (Login + Overview)**
  - Open `http://localhost:5173`. Highlight **Portfolio Demo · Synthetic Data** and **Local Mode (DuckDB)** badges (zero cloud cost).
  - Sign in as `admin` (show 3-role RBAC: Administrator, Data Steward, Risk Analyst).
  - On **Overview**, walk through the 8 live KPIs (`97,375` curated transactions, `$34.33M` volume, `99.74%` quality score, `3,633` suspicious risk indicators) and the 7-dimension quality chart.

- **0:35 – 1:15 | ETL, Standardization & Zero Silent Drops (Data Ingestion + Data Quality)**
  - Open **Data Ingestion**: show `JOB-BOOTSTRAP-100K` (`100,000` received → `97,375` valid, `2,625` quarantined, `375` duplicates, `8.52s`) and explain SHA-256 idempotency.
  - Open **Data Quality**: explain the 7 quality dimensions and 12 configurable rules, show how `"USA"`/`"United Kingdom"` standardize to `"US"`/`"GB"`, and show **Quarantined Records** where bad rows are preserved with rule IDs for Data Steward remediation (`OPEN → REVIEWED → RESOLVED`).

- **1:15 – 2:00 | Data Governance (Catalog, Lineage, Policies & Audit Logs)**
  - Open **Data Catalog & Business Glossary**: show table ownership (Business Owner, Technical Owner, Data Steward), classification (`Restricted` card token masking `****1234`), and standardized KPI definitions.
  - Open **Data Lineage**: trace `Source Files → Raw → Staging → Curated / Quarantine → Analytics → Dashboard`.
  - Briefly show **Governance Policies** (`POL-001` quality threshold enforcement) and **Audit Logs**.

- **2:00 – 2:40 | Risk Analytics (Fraud Analytics + Credit Risk)**
  - Open **Fraud Analytics**: highlight the disclaimer (*risk indicators, not confirmed fraud*), show explainable per-transaction triggers (amount spike, 15-minute velocity burst, geo-mismatch), and show measured IsolationForest evaluation (`0.8254` precision, `0.8581` PR-AUC, zero label leakage).
  - Open **Credit Risk**: show portfolio utilization, delinquency distribution, and explainable demonstration credit scoring.

- **2:40 – 3:00 | Free Cloud Portability (Reports & BigQuery Sandbox)**
  - Open **Reports**, click **Export BigQuery Sandbox CSVs**, and explain how those 5 CSVs (`raw_transactions.csv`, `cleaned_transactions.csv`, `quarantined_records.csv`, `fraud_analytics.csv`, `credit_risk_analytics.csv`) upload directly into BigQuery Sandbox to run the `sql/bigquery_sandbox/` analytics suite with zero billing.

---

## Core Technical Talking Points (Python, SQL, ETL, Governance, BigQuery, Risk)

1. **Python & ETL:** Vectorized Pandas/NumPy validation processes 100k rows in ~8.5s; SHA-256 checksums prevent duplicate batch ingestion.
2. **SQL:** BigQuery Sandbox & DuckDB queries use CTEs, `COUNTIF` / conditional aggregation, `ROW_NUMBER()` deduplication, `RANK()`, `LAG`/`LEAD`, and 7-day rolling averages (`ROWS BETWEEN 6 PRECEDING AND CURRENT ROW`) without unsupported Sandbox DML.
3. **Data Governance & Quality:** Combines technical controls (schema validation, quarantine, card masking) with governance metadata (stewardship, business glossary, lineage, policies, audit trail).
4. **Risk Analytics:** Fraud rules remain transparent for analysts while IsolationForest is strictly evaluated on held-out synthetic splits without label leakage.
