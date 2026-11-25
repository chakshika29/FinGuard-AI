# FinGuard AI — Technical Interview Preparation Guide

## Core Architecture & Governance Deep Dive

- **Why BigQuery Was Selected**: Serverless separation of storage (Capacitor columnar format) and compute (Dremel execution engine), native day-partitioning and clustering on multi-million-row financial ledgers, built-in dry-run cost estimation, and direct Power BI connector support.
- **BigQuery Partitioning & Clustering**: `finguard_curated.transactions` is partitioned by `transaction_date` (`DAY`) and clustered by `transaction_country`, `merchant_category`, and `fraud_risk_level`. Partitioning eliminates scanning out-of-range dates; clustering co-locates high-cardinality filter columns within storage blocks.
- **ETL vs. ELT**: FinGuard AI uses a hybrid medallion pattern — raw files land unaltered in `finguard_raw` (ELT preservation), followed by Python/SQL standardization, quarantine routing, and deduplicated loading into `finguard_curated`.
- **Data Governance vs. Data Management**: Data Management is the technical execution (ETL, pipelines, storage, schemas), whereas Data Governance defines the policies, ownership, stewardship, classification, quality thresholds, and auditability that control how data is managed.
- **Challenges Faced During Implementation & Real Solutions**:
  1. *Series Index Mismatch in Vectorized Scoring*: Sorting the transaction DataFrame for `LAG`-like velocity calculation changed row indices relative to an earlier `groupby().transform()` Series. Fixed by sorting & resetting index before feature derivations.
  2. *Windows Application Control Blocking Cython `.pyd` DLLs*: WDAC on the local Windows host blocked `sklearn.tree._quad_tree.pyd`. Solved by implementing a graceful pure-NumPy `PureNumpyIsolationForest` fallback (Liu-Ting-Zhou algorithm) that automatically activates only when `sklearn.ensemble` DLLs are blocked, while preserving `sklearn.ensemble.IsolationForest` on Linux/Docker/CI.
  3. *Zero Silent Data Loss at 100k+ Scale*: Iterating row-by-row over 100,000 rows in Python is slow; solved by vectorizing all 12 validation rules in NumPy/Pandas and only serializing the ~2.6% invalid rows into `quarantined_records`.

---

## 30 Technical Interview Questions & Answers

1. **Q: How does FinGuard AI achieve idempotent ingestion?**
   A: Each uploaded/generated file is hashed with SHA-256 (`compute_sha256`). Before running ETL, the pipeline checks `ingestion_jobs` for a prior completed job with the same checksum (unless `force_reprocess=True`). Additionally, `transaction_id` uniqueness is enforced both within the batch (`duplicated()`) and against existing curated IDs (`INSERT OR IGNORE` / BigQuery `MERGE`).
2. **Q: Why do you preserve invalid records instead of filtering them out?**
   A: Silent deletion violates financial auditability and masks upstream source bugs. Quarantining rejected rows in `finguard_governance.quarantined_records` with `failure_reasons` and `remediation_status` enables root-cause remediation by Data Stewards.
3. **Q: Explain the 7 Data Quality dimensions implemented.**
   A: Completeness (null checks), Accuracy (numeric ranges), Consistency (standardized ISO country & status enums), Uniqueness (duplicate IDs), Validity (ISO-4217 currency & timestamp parsing), Timeliness (age SLA), and Referential Integrity (customer/merchant foreign keys).
4. **Q: How is the overall Data Quality Score calculated?**
   A: Each enabled rule calculates `pass_rate = (total - failed) / total * 100`. Dimension and overall scores are severity-weighted averages (`CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1`).
5. **Q: How do you prevent label leakage in your fraud ML model?**
   A: `fraud_label` is strictly excluded from the feature matrix `X` and from `StandardScaler.fit_transform`. `IsolationForest` trains unsupervised on non-label features on the 70% training split, and `fraud_label` is used solely post-hoc on the 30% held-out test split to compute Precision, Recall, F1, FPR, and PR-AUC.
6. **Q: Why use PR-AUC instead of only Accuracy for fraud detection?**
   A: Fraud is heavily imbalanced (~2.5% synthetic rate). A trivial all-zero classifier gets 97.5% accuracy while catching 0 fraud. PR-AUC and Precision/Recall directly evaluate positive-class detection quality.
7. **Q: Why choose DuckDB for local mode alongside BigQuery?**
   A: DuckDB is an embedded OLAP columnar engine supporting analytical window functions, schemas (`finguard_raw`, `finguard_curated`, etc.), and fast Pandas zero-copy registration, letting developers run 100k+ row analytics locally without cloud billing.
8. **Q: How does BigQuery dry-run cost estimation work?**
   A: Setting `bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)` lets BigQuery validate SQL and return `total_bytes_processed` without executing or charging for the query.
9. **Q: What is the difference between a Data Owner and a Data Steward?**
   A: The Data Owner (Business/Technical Owner) has ultimate accountability and budget/policy authority; the Data Steward handles day-to-day metadata curation, rule thresholds, glossary definitions, and quarantine remediation.
10. **Q: How do you detect velocity bursts in SQL and Pandas?**
    A: In BigQuery SQL, `LAG(transaction_timestamp) OVER (PARTITION BY customer_id ORDER BY transaction_timestamp)` computes `TIMESTAMP_DIFF(..., SECOND) <= 900`. In Pandas, we sort by `(customer_id, transaction_timestamp)` and take vectorized shifted epoch differences.
11. **Q: Why store raw payloads as `STRING` in `finguard_raw`?**
    A: Source files often contain type violations (e.g., `"INVALID_AMT"` in an amount column). Typing raw columns as `STRING` guarantees ingestion never crashes before logging and quarantining bad rows.
12. **Q: How does `ROW_NUMBER()` deduplication work in BigQuery?**
    A: `ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY processed_at ASC) = 1` deterministically retains the earliest arrival for each `transaction_id` before `MERGE`.
13. **Q: What happens when a country arrives as `"United States"` or `"USA"`?**
    A: The standardization layer maps known variants via `COUNTRY_STANDARDIZATION_MAP` to ISO-3166 `"US"` in `finguard_staging`, resolving consistency issues without rejecting valid transactions.
14. **Q: How is sensitive card data protected?**
    A: Synthetic card tokens are classified `Restricted` in the Data Catalog and masked (`****1234`) in API responses, React drawers, and CSV/Power BI exports.
15. **Q: Explain your RBAC model.**
    A: FastAPI `require_roles(...)` dependencies inspect the verified JWT role claim (`Administrator`, `Data Steward`, `Risk Analyst`) and return HTTP 403 when an unauthorized role attempts restricted mutations.
16. **Q: Why use asynchronous background jobs for file ingestion?**
    A: Ingesting 100k–1M rows can take several seconds; queuing jobs via FastAPI `BackgroundTasks` returns HTTP 200 immediately with `job_id` while the UI polls `GET /api/ingestion/jobs`.
17. **Q: What are the limitations of an application-level audit log?**
    A: While the API only exposes `INSERT` (no `UPDATE`/`DELETE` endpoints) on `audit_logs`, it resides in SQLite/SQL rather than immutable WORM storage (like GCS Object Lock or Cloud Audit Logs).
18. **Q: How does Credit Risk scoring differ from Fraud Risk scoring?**
    A: Fraud Risk evaluates *per-transaction* behavioral anomalies (amount spikes, velocity, geo-mismatch, device). Credit Risk evaluates *account-level* solvency and exposure (credit utilization ratio, repayment status, delinquency days).
19. **Q: Why separate `finguard_analytics` marts from `finguard_curated`?**
    A: Pre-aggregating daily and merchant metrics avoids scanning raw/curated transaction rows on every dashboard load and accelerates Power BI consumption.
20. **Q: How do you handle schema drift on uploaded files?**
    A: Column aliases (`txn_id` → `transaction_id`, `amt` → `transaction_amount`) are mapped cleanly, while missing mandatory structural columns raise an explicit `Schema mismatch` failure recorded on the `IngestionJob`.
21. **Q: What SQL optimization prevents full scans in `sql/bigquery/03_fraud_and_window_analytics.sql`?**
    A: Filtering on the partition column `WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)` prunes older date partitions.
22. **Q: How is the synthetic dataset kept reproducible?**
    A: Using `numpy.random.default_rng(seed)` so identical seeds produce identical customer cohorts, fraud counts, and injected quality issue distributions.
23. **Q: What is the difference between `Clustering` and `Partitioning` in BigQuery?**
    A: Partitioning physically divides a table into segments (e.g., by day) with strict query cost pruning guarantees; Clustering sorts data within each partition by up to 4 columns to accelerate `WHERE` and `GROUP BY` filters.
24. **Q: How would you scale this pipeline from 1M to 100M+ rows?**
    A: Stream/load partitioned Parquet files via GCS → BigQuery Load Jobs, push transformations into BigQuery SQL (`ELT` via dbt or Dataform), and replace SQLite metadata with Cloud SQL (PostgreSQL) + Cloud Tasks/PubSub workers.
25. **Q: What makes a Fraud Risk Score "explainable"?**
    A: Instead of outputting an opaque probability, every flagged transaction stores the exact triggered rule reasons (e.g., `"Multiple transactions detected within a 15-minute velocity window"`) for analyst auditability.
26. **Q: How do Governance Policies interact with Data Quality runs?**
    A: `POL-001` dynamically evaluates the latest `QualityCheckRun.overall_score >= 95.0` and flags `BREACHED` if quality drops below threshold.
27. **Q: Why use `JOIN` vs `EXISTS` in referential integrity SQL?**
    A: `LEFT JOIN ... WHERE target.key IS NULL` or `NOT EXISTS` avoids multiplying rows when checking missing foreign keys against master tables.
28. **Q: How do you ensure Power BI works even without cloud billing?**
    A: By providing both a BigQuery Direct Connector Power Query M script AND an automated `powerbi_bundle` CSV star-schema exporter with matching DAX measures.
29. **Q: Why use `bcrypt` instead of SHA-256 for passwords?**
    A: SHA-256 is fast and vulnerable to GPU brute-forcing; `bcrypt` is intentionally memory/compute-hard with built-in per-password salting.
30. **Q: How would you handle PII if real customer data replaced synthetic data?**
    A: Implement tokenization at ingestion via Cloud DLP, column-level IAM policy tags in BigQuery, VPC Service Controls, and KMS customer-managed encryption keys (CMEK).
