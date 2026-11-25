# FinGuard AI — Credit & Fraud Risk Data Governance Platform

**A portfolio project built for the American Express Analyst – Data Governance & Management role, demonstrating enterprise ETL, 7-dimension data quality, metadata governance, fraud/credit risk analytics, and Google BigQuery Sandbox SQL.**

> **Zero-Cost & Synthetic Data Notice:** The web platform runs **100% free locally** on **DuckDB + SQLite** without cloud credentials, billing, Docker, or Power BI Desktop. Cloud analytics were verified separately in **Google BigQuery Sandbox** via manual browser CSV upload (**no live backend-to-BigQuery connectivity**). All financial records are **100% synthetic**; fraud flags are risk indicators (not confirmed fraud), and credit scores are educational demonstrations only.

---

## Business Problem & Solution

Financial institutions process high-volume payment feeds where schema mismatches, duplicate IDs, missing fields, and inconsistent country/currency codes degrade risk reporting. **FinGuard AI** implements a 5-layer medallion governance architecture (`Raw → Staging → Curated → Quarantine → Analytics`):

- **Standardized ETL & Zero Silent Drops:** Vectorized Python/Pandas ETL with SHA-256 idempotency, ISO country/currency normalization, and quarantine routing for invalid/duplicate rows.
- **7-Dimension Data Quality Engine:** Evaluates Completeness, Accuracy, Consistency, Uniqueness, Validity, Timeliness, and Referential Integrity with severity-weighted scoring and steward remediation.
- **Data Governance Module:** Searchable Data Catalog, Business/Technical Ownership & Data Stewardship, Business Glossary, 4-tier Classification + card token masking (`****xxxx`), Data Lineage diagram, Governance Policies, and Append-Only Audit Logs.
- **Fraud & Credit Risk Analytics:** Explainable rule-based fraud scoring (0–100), Liu-Ting-Zhou `IsolationForest` anomaly evaluation (zero label leakage), and portfolio credit utilization/delinquency monitoring.
- **Verified BigQuery Sandbox Cloud SQL:** Exported CSVs uploaded manually in browser to **Google BigQuery Sandbox** (`finguard-ai-515807`) for live serverless SQL analytics at zero cost.

---

## Architecture

```
[Synthetic Generator / CSV & JSON Upload]
                 │  (SHA-256 Checksum & Idempotency Check)
                 ▼
      [1. finguard_raw] ──── Raw records preserved untouched (DuckDB Local)
                 │  (Standardize ISO codes, parse types/dates)
                 ▼
    [2. finguard_staging] ── 12 vectorized quality validations
         │             │
   (Valid)             (Invalid / Duplicate / Orphan)
         │             ▼
         │   [4. finguard_governance.quarantined_records]
         ▼
   [3. finguard_curated] ─── Deduplicated ledger + Fraud & Credit Risk
         │
         ▼
  [5. finguard_analytics] ── Daily & Merchant Risk Summary Marts (DuckDB)
         │
   ┌─────┴────────────────────────────────────────┐
   ▼                                              ▼
[FastAPI + 12-Page React UI]        [Manual CSV Export → Browser Upload]
 (Local Execution: DuckDB)                        ▼
                                    [Google BigQuery Sandbox (Cloud SQL)]
                                     Project: finguard-ai-515807 | 0 Billing
```

> *Note: The FastAPI backend executes strictly against the local DuckDB warehouse (`DATA_BACKEND=local`). BigQuery Sandbox is used as a decoupled cloud SQL analytics layer via browser-uploaded CSVs (no live backend-to-BigQuery connection).*

---

## Tech Stack

- **Data Engineering & Analytics:** Python 3.11, Pandas, NumPy, DuckDB (local warehouse), SQL, Scikit-learn (`metrics`/`preprocessing`) + Pure-NumPy `IsolationForest`
- **Cloud SQL (Zero-Billing Sandbox):** Google BigQuery Sandbox (`finguard_analytics` dataset, manual CSV upload)
- **Backend & Security:** FastAPI, SQLAlchemy, Pydantic, PyJWT (3-role RBAC: Administrator, Data Steward, Risk Analyst), `bcrypt`, Pytest, Ruff
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, Axios, Vitest

---

## Verified Local & BigQuery Sandbox Results

### 1. Local DuckDB Benchmark (Initial 100,000-Record Seed)
- **Dataset Size:** `100,000` synthetic transactions (`seed=42`, `3,105` synthetic fraud records, `3,000` injected quality defects)
- **Generation / ETL Time:** `6.00s` generation | `8.52s` full ETL + quality checks + fraud scoring
- **Outcome:** `97,375` clean curated records | `375` country variants standardized (`"USA"`/`"United Kingdom"` → `"US"`/`"GB"`) | `2,625` quarantined records (including `375` duplicates)
- **Anomaly Detection (`IsolationForest (Pure-NumPy Fallback)`, 70/30 held-out split, zero label leakage):**
  - Precision: **0.8254** | Recall: **0.7661** | F1-Score: **0.7947** | PR-AUC: **0.8581** | FPR: **0.0053** (`TP=714, FP=151, FN=218, TN=28,130`)
  *(Uses `PureNumpyIsolationForest` on Windows hosts where WDAC blocks `sklearn.tree` DLLs; uses `sklearn.ensemble.IsolationForest` on Linux/CI.)*

### 2. Cumulative Dataset & Verified BigQuery Sandbox Execution (120,000 Records)
- Following the initial `100,000`-record seed (`JOB-BOOTSTRAP-100K`), two `10,000`-record verification ingestion runs (`JOB-64C3CDC6E6` and `JOB-6D004DABE4`, `seed=101`) brought cumulative raw records in DuckDB to **120,000** (`107,112` curated + `12,888` quarantined).
- **Verified BigQuery Sandbox Details:**
  - **GCP Project ID:** `finguard-ai-515807` (Free BigQuery Sandbox, zero billing)
  - **Dataset & Table:** `finguard_analytics.raw_transactions` (browser CSV upload)
  - **Verified BigQuery Record Count:** **120,000**
  - **Merchant Categories Returned:** **10**
  - **Merchant Analytics Query Scan:** **2.34 MB** processed

---

## Quick Start on Windows (No Docker, No Cloud Billing)

```powershell
# 1. Setup virtual environment and install dependencies
python -m venv .venv
.\.venv\Scripts\pip.exe install -r backend/requirements.txt
Copy-Item .env.example .env

# 2. Initialize DuckDB warehouse & seed 100,000 synthetic records
.\.venv\Scripts\python.exe scripts/init_and_seed.py 100000

# 3. Start FastAPI backend (Terminal 1)
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 4. Start React frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

- **Frontend:** `http://localhost:5173` | **Swagger API Docs:** `http://localhost:8000/docs`
- **Demo Accounts:** `admin` / `Admin@FinGuard2026!`, `steward` / `Steward@FinGuard2026!`, `analyst` / `Analyst@FinGuard2026!`
- **Run Tests:** `.\.venv\Scripts\python.exe -m pytest backend/tests/ -v` and `cd frontend; npm test -- --run`

---

## Documentation

- [Verification Report (Local + BigQuery Sandbox)](docs/VERIFICATION_REPORT.md)
- [BigQuery Sandbox Browser Guide](docs/BIGQUERY_SANDBOX_GUIDE.md)
- [SQL Queries & Business Purpose](docs/SQL_EXPLANATION.md)
- [Data Governance Methodology](docs/DATA_GOVERNANCE.md)
- [3-Minute Demo & Interview Script](docs/DEMO_SCRIPT.md)
- [Technical Interview Q&A (30 Questions)](docs/INTERVIEW_PREPARATION.md)
