# Beginner Guide: Running FinGuard AI Queries in Google BigQuery Sandbox (100% Free)

This guide shows you how to upload FinGuard AI's synthetic CSV datasets and run enterprise SQL queries in **Google BigQuery Sandbox** directly in your web browser—with **zero credit card, zero billing account, zero Cloud Storage (GCS), and zero service-account keys**.

---

## Step 1: Export the BigQuery Sandbox CSV Files Locally

Either click **Export BigQuery Sandbox CSVs** on the **Reports** page in the FinGuard AI UI, or run in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\export_bigquery_sandbox_csvs.py
```

This generates 5 clean CSV files in `data\bigquery_sandbox\` (each well under BigQuery's 100 MB browser upload limit):
1. `raw_transactions.csv` (~33 MB)
2. `cleaned_transactions.csv` (~25 MB)
3. `quarantined_records.csv` (~0.6 MB)
4. `fraud_analytics.csv` (~17 MB)
5. `credit_risk_analytics.csv` (~1.1 MB)

---

## Step 2: Open BigQuery Sandbox in Your Browser

1. Open [https://console.cloud.google.com/bigquery](https://console.cloud.google.com/bigquery) and sign in with any standard Google account.
2. If you do not have a project yet, click **Create Project** (e.g., name it `finguard-sandbox-demo`), then select it.
3. Confirm the **SANDBOX** banner appears at the top of the BigQuery Studio page (no billing or credit card is needed; Sandbox includes **10 GB storage** and **1 TiB/month of SQL queries** free).

---

## Step 3: Create the `finguard_sandbox` Dataset

1. In the **Explorer** pane on the left, click the three dots (`⋮`) next to your project ID → **Create dataset**.
2. Set **Dataset ID** to `finguard_sandbox`.
3. Set **Location type** to **Multi-region → US**.
4. Click **Create dataset**.

---

## Step 4: Upload the 5 CSV Files Manually

Repeat these steps for each of the 5 CSV files in `data\bigquery_sandbox\`:

1. Click the three dots (`⋮`) next to `finguard_sandbox` → **Create table**.
2. Under **Source**:
   - **Create table from**: `Upload`
   - **Select file**: Browse to `data\bigquery_sandbox\<filename>.csv`
   - **File format**: `CSV`
3. Under **Destination**:
   - **Table**: Enter the exact matching table name:
     - `raw_transactions`
     - `cleaned_transactions`
     - `quarantined_records`
     - `fraud_analytics`
     - `credit_risk_analytics`
4. Under **Schema**: Check **Auto detect**.
5. Click **Create table**.

> **Tip:** If you see an auto-detect type warning on `raw_transactions` (because `raw_transactions.csv` intentionally contains invalid strings like `"INVALID_AMT"`), expand **Advanced options** and set **Header rows to skip** = `1`, or let BigQuery infer `STRING` for messy columns.

---

## Step 5: Execute the Sandbox SQL Scripts

Open the SQL files in `sql\bigquery_sandbox\`, copy each query into a **New SQL Query** tab in BigQuery Studio, check the green query validator (which shows bytes processed), and click **Run**:

1. `01_total_and_duplicate_analysis.sql` — Portfolio totals & duplicate `transaction_id` detection (`GROUP BY` + `HAVING`).
2. `02_missing_values_and_data_quality.sql` — Missing mandatory fields, non-numeric amounts, invalid timestamps/currencies, and pass-rate scoring.
3. `03_data_standardization_ctas.sql` — Creates a standardized table (`CREATE OR REPLACE TABLE ... AS SELECT` + `QUALIFY ROW_NUMBER()`) mapping `"USA"`/`"United States"` → `"US"`, parsing types, and deduplicating without DML `MERGE`.
4. `04_customer_and_merchant_risk.sql` — Customer spending patterns & merchant category `RANK()`.
5. `05_fraud_and_window_functions.sql` — Fraud severity distribution, flagged transactions, `LAG`/`LEAD` daily deltas, and 7-day rolling averages.
6. `06_credit_utilization_and_governance.sql` — Credit utilization by segment, overdue rates, and quarantine remediation summary.

> **Important Sandbox Limitation:** BigQuery Sandbox does not allow DML statements (`MERGE`, `UPDATE`, `DELETE`) or streaming inserts. All queries in `sql/bigquery_sandbox/` use `SELECT`, CTEs, views, and `CREATE OR REPLACE TABLE ... AS SELECT` so they run cleanly in Sandbox at zero cost.
