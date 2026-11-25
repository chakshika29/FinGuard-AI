# Beginner Google Cloud Platform (GCP) Setup Guide

This guide walks through configuring Google Cloud Storage (GCS) and Google BigQuery for FinGuard AI without enabling paid services unexpectedly.

## 1. BigQuery Sandbox vs. Billing

- **BigQuery Sandbox** allows free dataset creation, table loading from local files, and up to **1 TiB/month of query processing** and **10 GB/month of active storage** without a credit card.
- **Operations requiring billing**: Creating a **Google Cloud Storage (GCS)** bucket beyond free limits, running **Google Cloud Run** deployments, or using BigQuery streaming inserts / DML `MERGE` statements (Sandbox restricts DML/streaming; batch loads and `SELECT` analytics work in Sandbox).

## 2. Step-by-Step Setup

### Step 1: Create a GCP Project
1. Sign in to [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project → New Project**, name it e.g. `finguard-ai-demo`, and note your `GCP_PROJECT_ID`.

### Step 2: Enable Required APIs
In Cloud Console (or via `gcloud` CLI):
```bash
gcloud services enable bigquery.googleapis.com storage.googleapis.com
```

### Step 3: Configure Authentication (No Hardcoded Secrets)
**Option A — Local Development via Application Default Credentials (Recommended):**
```bash
gcloud auth application-default login
gcloud config set project YOUR_GCP_PROJECT_ID
```

**Option B — Service Account (Minimum IAM Permissions):**
1. Create a Service Account `finguard-etl-sa`.
2. Grant minimum roles:
   - `roles/bigquery.dataEditor` (read/write dataset tables)
   - `roles/bigquery.jobUser` (execute queries & load jobs)
   - `roles/storage.objectAdmin` (if using GCS bucket uploads)
3. Download the JSON key outside the repository (e.g. `C:\Users\<you>\keys\finguard-sa.json`) and set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`. **Never commit JSON keys to Git.**

### Step 4: Configure `.env`
```env
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=US
GCS_BUCKET_NAME=your-finguard-raw-bucket
DATA_BACKEND=bigquery
```

### Step 5: Provision BigQuery Datasets & Partitioned Tables
```powershell
.\.venv\Scripts\python.exe cloud\gcp\setup_gcp_resources.py
```
This creates `finguard_raw`, `finguard_staging`, `finguard_curated`, `finguard_governance`, `finguard_analytics`, and the day-partitioned, clustered `finguard_curated.transactions` table.

### Step 6: Load Sample Data & Run Dry-Run Cost Check
```powershell
.\.venv\Scripts\python.exe cloud\bigquery\run_bq_jobs.py --file data\sample\finguard_seed_100000_42_*.csv --dry-run-sql sql\bigquery\03_fraud_and_window_analytics.sql
```
