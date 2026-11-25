# FinGuard AI — System Architecture

> **Synthetic Data Notice:** All financial records, card tokens, accounts, and merchant records in FinGuard AI are 100% synthetic.

## 1. Local DuckDB + Decoupled BigQuery Sandbox Architecture

FinGuard AI uses a 5-layer medallion warehouse pattern (`finguard_raw` → `finguard_staging` → `finguard_curated` → `finguard_governance` → `finguard_analytics`):

- **Local Execution (`DATA_BACKEND=local`, default):** FastAPI and the React UI execute directly against **DuckDB** (`data/processed/finguard_warehouse.duckdb`) and **SQLite** metadata (`data/processed/finguard_metadata.db`), requiring zero cloud credentials or billing.
- **Cloud SQL Analytics (BigQuery Sandbox):** Clean and raw CSV datasets exported by FinGuard AI (`data/bigquery_sandbox/`) are uploaded manually through the Google Cloud Console browser UI into **BigQuery Sandbox** (`finguard-ai-515807` / `finguard_analytics`) to run serverless SQL analytics at zero cost. There is **no live backend-to-BigQuery connection** in Sandbox mode.

```
[Synthetic Generator / CSV & JSON Upload]
                 │  (SHA-256 Checksum & Idempotency Guard)
                 ▼
       [1. finguard_raw]  ─── Raw payloads preserved as strings (DuckDB)
                 │  (Standardize ISO codes, types, timestamps)
                 ▼
     [2. finguard_staging] ── Row-level DQ validation flags (DuckDB)
          │            │
    (Valid)            (Invalid / Duplicate / Orphan)
          │            ▼
          │   [4. finguard_governance.quarantined_records]
          ▼
    [3. finguard_curated] ─── Deduplicated ledger + Fraud Score + Credit Risk
                 │
                 ▼
   [5. finguard_analytics] ── Daily & Merchant Risk Marts (DuckDB)
                 │
       ┌─────────┴────────────────────────────────────┐
       ▼                                              ▼
 [FastAPI + React UI]                    [CSV Export → Manual Browser Upload]
 (Local Mode: DuckDB)                                 ▼
                                         [Google BigQuery Sandbox (Free Tier)]
                                          Serverless SQL Analytics (No Billing)
```

## 2. Backend Module Layout

- `backend/app/core/`: Settings (`config.py`), structured JSON logging (`logging.py`), JWT/bcrypt/RBAC/masking (`security.py`), DuckDB + SQLAlchemy database managers (`database.py`), seeding (`bootstrap.py`).
- `backend/app/pipelines/`: Seeded synthetic generator (`generator.py`) and vectorized ETL pipeline (`etl.py`).
- `backend/app/data_quality/`: Configurable 7-dimension quality scoring engine (`engine.py`).
- `backend/app/governance/`: Append-only application audit service (`audit_service.py`), catalog, glossary, lineage, and policy routes.
- `backend/app/fraud_detection/`: Explainable rule-based scoring + zero-leakage `IsolationForest` (`PureNumpyIsolationForest` fallback on WDAC-locked Windows, `sklearn.ensemble.IsolationForest` on Linux/CI).
- `backend/app/credit_risk/`: Portfolio & account credit utilization/delinquency calculator (`engine.py`).
- `backend/app/services/gcp_service.py`: Optional `google-cloud-bigquery` / `google-cloud-storage` helper (unused in default Local Mode).
