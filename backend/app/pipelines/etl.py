"""Enterprise ETL Pipeline: Extract, Standardize, Validate, Quarantine, Curate, and Refresh Marts."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal, duckdb_session
from backend.app.core.logging import get_logger
from backend.app.governance.audit_service import record_audit_log
from backend.app.models.metadata import DataCatalogEntry, IngestionJob, LineageEvent

logger = get_logger(__name__)

COUNTRY_STANDARDIZATION_MAP = {
    "US": "US", "USA": "US", "U.S.": "US", "U.S.A.": "US", "UNITED STATES": "US", "UNITED STATES OF AMERICA": "US",
    "GB": "GB", "UK": "GB", "U.K.": "GB", "UNITED KINGDOM": "GB", "GREAT BRITAIN": "GB",
    "CA": "CA", "CAN": "CA", "CANADA": "CA",
    "IN": "IN", "IND": "IN", "INDIA": "IN",
    "SG": "SG", "SGP": "SG", "SINGAPORE": "SG",
    "DE": "DE", "DEU": "DE", "GERMANY": "DE", "DEUTCHLAND": "DE",
    "FR": "FR", "FRA": "FR", "FRANCE": "FR",
    "AU": "AU", "AUS": "AU", "AUSTRALIA": "AU",
    "JP": "JP", "JPN": "JP", "JAPAN": "JP",
    "AE": "AE", "ARE": "AE", "UAE": "AE",
    "BR": "BR", "BRA": "BR", "BRAZIL": "BR",
    "MX": "MX", "MEX": "MX", "MEXICO": "MX",
}

COLUMN_ALIASES = {
    "txn_id": "transaction_id",
    "tx_id": "transaction_id",
    "cust_id": "customer_id",
    "acct_id": "account_id",
    "amount": "transaction_amount",
    "amt": "transaction_amount",
    "tx_timestamp": "transaction_timestamp",
    "timestamp": "transaction_timestamp",
    "country": "transaction_country",
    "city": "transaction_city",
    "status": "transaction_status",
    "merch_id": "merchant_id",
    "mcc": "merchant_category",
}

REQUIRED_COLUMNS = [
    "transaction_id",
    "customer_id",
    "account_id",
    "transaction_timestamp",
    "transaction_amount",
    "currency",
    "merchant_id",
]

ALL_TX_COLUMNS = [
    "transaction_id",
    "customer_id",
    "account_id",
    "card_token",
    "transaction_timestamp",
    "transaction_amount",
    "currency",
    "merchant_id",
    "merchant_category",
    "transaction_type",
    "payment_method",
    "transaction_country",
    "transaction_city",
    "device_id",
    "transaction_status",
    "credit_limit",
    "outstanding_balance",
    "repayment_status",
    "customer_risk_category",
    "fraud_label",
    "ingestion_timestamp",
    "source_system",
]

VALID_CURRENCIES = {"USD", "EUR", "GBP", "CAD", "INR", "SGD", "AUD", "JPY"}
VALID_COUNTRIES = {"US", "GB", "CA", "IN", "SG", "DE", "FR", "AU", "JP", "AE", "BR", "MX"}
VALID_STATUSES = {"APPROVED", "DECLINED", "PENDING", "REVERSED", "FAILED"}


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_reference_tables(
    customers_file: str | Path | None = None,
    accounts_file: str | Path | None = None,
    merchants_file: str | Path | None = None,
) -> dict[str, int]:
    """Upsert synthetic customers, accounts, and merchants reference tables into DuckDB."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET
    counts = {"customers": 0, "accounts": 0, "merchants": 0}

    with duckdb_session() as conn:
        if customers_file and Path(customers_file).exists():
            cdf = pd.read_csv(customers_file, dtype=str).fillna("")
            cdf["account_open_date"] = pd.to_datetime(cdf["account_open_date"], errors="coerce").dt.date
            cdf["updated_at"] = datetime.now(timezone.utc)
            conn.register("tmp_customers_df", cdf)
            conn.execute(f"""
                INSERT OR REPLACE INTO {curated}.customers
                (customer_id, full_name_synthetic, customer_segment, customer_risk_category,
                 home_country, home_city, income_band, account_open_date, updated_at)
                SELECT customer_id, full_name_synthetic, customer_segment, customer_risk_category,
                       home_country, home_city, income_band, account_open_date, updated_at
                FROM tmp_customers_df
            """)
            conn.unregister("tmp_customers_df")
            counts["customers"] = len(cdf)

        if accounts_file and Path(accounts_file).exists():
            adf = pd.read_csv(accounts_file)
            adf["credit_limit"] = pd.to_numeric(adf["credit_limit"], errors="coerce").fillna(5000.0)
            adf["outstanding_balance"] = pd.to_numeric(adf["outstanding_balance"], errors="coerce").fillna(0.0)
            adf["credit_utilization_ratio"] = np.where(
                adf["credit_limit"] > 0,
                np.round(adf["outstanding_balance"] / adf["credit_limit"], 4),
                0.0,
            )
            adf["delinquency_days"] = pd.to_numeric(adf["delinquency_days"], errors="coerce").fillna(0).astype(int)
            # Explainable demonstration credit risk score (0-100)
            repay_penalty = adf["repayment_status"].map({
                "CURRENT": 5.0,
                "PAST_DUE_30": 32.0,
                "PAST_DUE_60": 55.0,
                "PAST_DUE_90": 78.0,
                "DEFAULT": 95.0,
            }).fillna(15.0)
            util_score = np.clip(adf["credit_utilization_ratio"] * 45.0, 0.0, 45.0)
            delinq_score = np.clip(adf["delinquency_days"] * 0.25, 0.0, 30.0)
            adf["credit_risk_score"] = np.round(np.clip(util_score * 0.45 + repay_penalty * 0.45 + delinq_score * 0.35, 0.0, 100.0), 2)
            adf["credit_risk_tier"] = np.select(
                [adf["credit_risk_score"] >= 70, adf["credit_risk_score"] >= 45, adf["credit_risk_score"] >= 25],
                ["CRITICAL", "HIGH", "MEDIUM"],
                default="LOW",
            )
            adf["updated_at"] = datetime.now(timezone.utc)
            conn.register("tmp_accounts_df", adf)
            conn.execute(f"""
                INSERT OR REPLACE INTO {curated}.accounts
                (account_id, customer_id, card_token, credit_limit, outstanding_balance,
                 credit_utilization_ratio, repayment_status, delinquency_days, account_status,
                 credit_risk_score, credit_risk_tier, updated_at)
                SELECT account_id, customer_id, card_token, credit_limit, outstanding_balance,
                       credit_utilization_ratio, repayment_status, delinquency_days, account_status,
                       credit_risk_score, credit_risk_tier, updated_at
                FROM tmp_accounts_df
            """)
            conn.unregister("tmp_accounts_df")
            counts["accounts"] = len(adf)

        if merchants_file and Path(merchants_file).exists():
            mdf = pd.read_csv(merchants_file, dtype=str).fillna("")
            mdf["updated_at"] = datetime.now(timezone.utc)
            conn.register("tmp_merchants_df", mdf)
            conn.execute(f"""
                INSERT OR REPLACE INTO {curated}.merchants
                (merchant_id, merchant_name, merchant_category, merchant_country, merchant_risk_tier, updated_at)
                SELECT merchant_id, merchant_name, merchant_category, merchant_country, merchant_risk_tier, updated_at
                FROM tmp_merchants_df
            """)
            conn.unregister("tmp_merchants_df")
            counts["merchants"] = len(mdf)

    return counts


def _read_transaction_file(file_path: Path) -> tuple[pd.DataFrame, str]:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        return df, "csv"
    if suffix == ".json":
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            return pd.DataFrame(), "json"
        if text.startswith("["):
            df = pd.read_json(file_path, dtype=str)
        else:
            df = pd.read_json(file_path, lines=True, dtype=str)
        return df.fillna("").astype(str), "json"
    raise ValueError(f"Unsupported file format '{suffix}'. Only .csv and .json are permitted.")


def execute_etl_job(
    job_id: str,
    file_path: str | Path,
    triggered_by: str = "system",
    customers_file: str | Path | None = None,
    accounts_file: str | Path | None = None,
    merchants_file: str | Path | None = None,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    """Execute full Extract -> Transform -> Validate -> Quarantine -> Load -> Risk Score -> Analytics pipeline."""
    db = SessionLocal()
    try:
        return run_etl_pipeline(
            db=db,
            job_id=job_id,
            file_path=file_path,
            triggered_by=triggered_by,
            customers_file=customers_file,
            accounts_file=accounts_file,
            merchants_file=merchants_file,
            force_reprocess=force_reprocess,
        )
    finally:
        db.close()


def run_etl_pipeline(
    db: Session,
    job_id: str,
    file_path: str | Path,
    triggered_by: str = "system",
    customers_file: str | Path | None = None,
    accounts_file: str | Path | None = None,
    merchants_file: str | Path | None = None,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    """Synchronous core ETL runner (called either directly in tests or via BackgroundTasks)."""
    from backend.app.data_quality.engine import run_quality_checks
    from backend.app.fraud_detection.engine import score_transactions_and_generate_alerts

    start_time = time.perf_counter()
    settings = get_settings()
    path = Path(file_path)
    checksum = compute_sha256(path)

    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        job = IngestionJob(
            id=job_id,
            source_file=path.name,
            file_format=path.suffix.lstrip(".").lower() or "csv",
            file_checksum=checksum,
            status="RUNNING",
            triggered_by=triggered_by,
            backend_target="bigquery" if settings.is_bigquery_mode else "local",
        )
        db.add(job)
    else:
        job.status = "RUNNING"
        job.file_checksum = checksum
    db.commit()

    try:
        # Load reference tables first if supplied
        if customers_file or accounts_file or merchants_file:
            load_reference_tables(customers_file, accounts_file, merchants_file)

        # Idempotency Check by SHA-256 Checksum
        if not force_reprocess:
            prior = (
                db.query(IngestionJob)
                .filter(
                    IngestionJob.file_checksum == checksum,
                    IngestionJob.id != job_id,
                    IngestionJob.status.in_(["COMPLETED", "COMPLETED_WITH_QUARANTINE"]),
                )
                .first()
            )
            if prior:
                df_check, fmt = _read_transaction_file(path)
                n_rows = len(df_check)
                duration = round(time.perf_counter() - start_time, 3)
                job.status = "COMPLETED_IDEMPOTENT"
                job.file_format = fmt
                job.records_received = n_rows
                job.records_processed = n_rows
                job.valid_records = 0
                job.invalid_records = 0
                job.duplicate_records = n_rows
                job.quarantined_records = 0
                job.idempotent_skip = True
                job.processing_duration_sec = duration
                job.completed_at = datetime.now(timezone.utc)
                record_audit_log(
                    db,
                    actor=triggered_by,
                    actor_role="System",
                    action="INGESTION_IDEMPOTENT_SKIP",
                    resource_type="ingestion_job",
                    resource_id=job_id,
                    updated_value=f"Skipped duplicate file checksum {checksum[:12]} (prior job {prior.id})",
                )
                db.commit()
                return {"job_id": job_id, "status": job.status, "idempotent_skip": True, "records_received": n_rows}

        # EXTRACT
        raw_df, fmt = _read_transaction_file(path)
        job.file_format = fmt
        records_received = len(raw_df)
        job.records_received = records_received

        if records_received == 0:
            raise ValueError("Uploaded transaction file contains 0 records.")

        # Standardize column names
        raw_df.columns = [
            COLUMN_ALIASES.get(c.strip().lower().replace(" ", "_"), c.strip().lower().replace(" ", "_"))
            for c in raw_df.columns
        ]

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in raw_df.columns]
        if missing_cols:
            raise ValueError(f"Schema mismatch: missing mandatory columns {missing_cols}")

        for col in ALL_TX_COLUMNS:
            if col not in raw_df.columns:
                raw_df[col] = ""

        raw_df = raw_df[ALL_TX_COLUMNS].copy()
        raw_df["ingestion_job_id"] = job_id
        raw_df["file_checksum"] = checksum
        raw_df["source_file"] = path.name
        raw_df["source_row_number"] = np.arange(1, records_received + 1, dtype=int)
        raw_df["loaded_at"] = datetime.now(timezone.utc)

        raw_schema = settings.BIGQUERY_RAW_DATASET
        staging_schema = settings.BIGQUERY_STAGING_DATASET
        curated_schema = settings.BIGQUERY_CURATED_DATASET
        gov_schema = settings.BIGQUERY_GOVERNANCE_DATASET
        analytics_schema = settings.BIGQUERY_ANALYTICS_DATASET

        # Load RAW layer
        with duckdb_session() as conn:
            conn.register("tmp_raw_df", raw_df)
            conn.execute(f"INSERT INTO {raw_schema}.transactions_raw SELECT * FROM tmp_raw_df")
            conn.unregister("tmp_raw_df")

            existing_tx_ids = set(
                conn.execute(f"SELECT transaction_id FROM {curated_schema}.transactions").fetchdf()["transaction_id"].tolist()
            )
            valid_customers = set(
                conn.execute(f"SELECT customer_id FROM {curated_schema}.customers").fetchdf()["customer_id"].tolist()
            )
            valid_merchants = set(
                conn.execute(f"SELECT merchant_id FROM {curated_schema}.merchants").fetchdf()["merchant_id"].tolist()
            )

        db.add(LineageEvent(
            job_id=job_id,
            transformation_name="Extract Raw File",
            source_layer="Source Files",
            source_table=path.name,
            destination_layer="Raw Dataset",
            destination_table=f"{raw_schema}.transactions_raw",
            records_in=records_received,
            records_out=records_received,
        ))

        # TRANSFORM & VALIDATE (Vectorized)
        stg = pd.DataFrame()
        stg["transaction_id"] = raw_df["transaction_id"].astype(str).str.strip()
        stg["customer_id"] = raw_df["customer_id"].astype(str).str.strip()
        stg["account_id"] = raw_df["account_id"].astype(str).str.strip()
        stg["card_token"] = raw_df["card_token"].astype(str).str.strip()

        parsed_ts = pd.to_datetime(raw_df["transaction_timestamp"], errors="coerce", utc=True)
        stg["transaction_timestamp"] = parsed_ts

        parsed_amt = pd.to_numeric(raw_df["transaction_amount"], errors="coerce")
        stg["transaction_amount"] = parsed_amt

        stg["currency"] = raw_df["currency"].astype(str).str.strip().str.upper()
        stg["merchant_id"] = raw_df["merchant_id"].astype(str).str.strip()
        stg["merchant_category"] = raw_df["merchant_category"].astype(str).str.strip().str.upper()
        stg["transaction_type"] = raw_df["transaction_type"].astype(str).str.strip().str.upper()
        stg["payment_method"] = raw_df["payment_method"].astype(str).str.strip().str.upper()

        raw_country_upper = raw_df["transaction_country"].astype(str).str.strip().str.upper()
        stg["transaction_country"] = raw_country_upper.map(COUNTRY_STANDARDIZATION_MAP).fillna(raw_country_upper)
        stg["transaction_city"] = raw_df["transaction_city"].astype(str).str.strip().str.title()
        stg["device_id"] = raw_df["device_id"].astype(str).str.strip()

        raw_status = raw_df["transaction_status"].astype(str).str.strip().str.upper()
        stg["transaction_status"] = np.where(raw_status == "", "UNKNOWN", raw_status)

        stg["credit_limit"] = pd.to_numeric(raw_df["credit_limit"], errors="coerce")
        stg["outstanding_balance"] = pd.to_numeric(raw_df["outstanding_balance"], errors="coerce").fillna(0.0)
        stg["repayment_status"] = raw_df["repayment_status"].astype(str).str.strip().str.upper().replace("", "CURRENT")
        stg["customer_risk_category"] = raw_df["customer_risk_category"].astype(str).str.strip().str.upper().replace("", "MEDIUM")
        stg["fraud_label"] = pd.to_numeric(raw_df["fraud_label"], errors="coerce").fillna(0).astype(int)

        parsed_ing_ts = pd.to_datetime(raw_df["ingestion_timestamp"], errors="coerce", utc=True).fillna(pd.Timestamp.now(tz="UTC"))
        stg["ingestion_timestamp"] = parsed_ing_ts
        stg["source_system"] = raw_df["source_system"].astype(str).str.strip().replace("", "BATCH_UPLOAD")
        stg["ingestion_job_id"] = job_id

        # Vectorized Validation Masks
        now_utc = pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)
        err_missing_tx = stg["transaction_id"] == ""
        err_missing_cust = stg["customer_id"] == ""
        err_missing_merch = stg["merchant_id"] == ""
        err_bad_ts = stg["transaction_timestamp"].isna() | (stg["transaction_timestamp"] > now_utc)
        err_bad_amt = stg["transaction_amount"].isna() | (stg["transaction_amount"] < 0.01) | (stg["transaction_amount"] > 250000.0)
        err_bad_curr = ~stg["currency"].isin(VALID_CURRENCIES)
        err_bad_country = ~stg["transaction_country"].isin(VALID_COUNTRIES)
        err_bad_limit = stg["credit_limit"].isna() | (stg["credit_limit"] <= 0.0)
        err_dup_batch = (~err_missing_tx) & stg["transaction_id"].duplicated(keep="first")
        err_dup_existing = (~err_missing_tx) & stg["transaction_id"].isin(existing_tx_ids)

        if valid_customers:
            err_ref_cust = (~err_missing_cust) & (~stg["customer_id"].isin(valid_customers))
        else:
            err_ref_cust = pd.Series(False, index=stg.index)

        if valid_merchants:
            err_ref_merch = (~err_missing_merch) & (~stg["merchant_id"].isin(valid_merchants))
        else:
            err_ref_merch = pd.Series(False, index=stg.index)

        any_error = (
            err_missing_tx
            | err_missing_cust
            | err_missing_merch
            | err_bad_ts
            | err_bad_amt
            | err_bad_curr
            | err_bad_country
            | err_bad_limit
            | err_dup_batch
            | err_dup_existing
            | err_ref_cust
            | err_ref_merch
        )

        # Build concise vectorized error strings
        error_series = pd.Series("", index=stg.index, dtype=object)
        rule_checks = [
            (err_missing_tx, "Missing transaction_id [DQ-001]"),
            (err_missing_cust, "Missing customer_id [DQ-002]"),
            (err_missing_merch, "Missing merchant_id [DQ-010]"),
            (err_bad_ts, "Invalid or future timestamp [DQ-007]"),
            (err_bad_amt, "Invalid or non-numeric amount [DQ-006]"),
            (err_bad_curr, "Invalid ISO-4217 currency [DQ-004]"),
            (err_bad_country, "Unrecognized country code [DQ-005]"),
            (err_bad_limit, "Invalid credit_limit [DQ-012]"),
            (err_dup_batch | err_dup_existing, "Duplicate transaction_id [DQ-003]"),
            (err_ref_cust, "Unknown customer_id reference [DQ-009]"),
            (err_ref_merch, "Unknown merchant_id reference [DQ-010]"),
        ]
        for mask, label in rule_checks:
            error_series = np.where(
                mask,
                np.where(error_series == "", label, error_series + "; " + label),
                error_series,
            )

        stg["is_valid"] = ~any_error
        stg["validation_errors"] = error_series
        stg["processed_at"] = datetime.now(timezone.utc)

        # Convert timestamps to naive UTC for DuckDB TIMESTAMP columns
        stg_db = stg.copy()
        stg_db["transaction_timestamp"] = stg_db["transaction_timestamp"].dt.tz_convert(None)
        stg_db["ingestion_timestamp"] = stg_db["ingestion_timestamp"].dt.tz_convert(None)

        # Load STAGING layer
        with duckdb_session() as conn:
            conn.register("tmp_stg_df", stg_db)
            conn.execute(f"INSERT INTO {staging_schema}.transactions_staging SELECT * FROM tmp_stg_df")
            conn.unregister("tmp_stg_df")

        db.add(LineageEvent(
            job_id=job_id,
            transformation_name="Standardize & Validate Schema",
            source_layer="Raw Dataset",
            source_table=f"{raw_schema}.transactions_raw",
            destination_layer="Staging Dataset",
            destination_table=f"{staging_schema}.transactions_staging",
            records_in=records_received,
            records_out=records_received,
        ))

        # Split Valid vs Quarantined
        valid_df = stg_db[stg_db["is_valid"]].copy()
        invalid_mask = ~stg_db["is_valid"]
        invalid_raw = raw_df[invalid_mask].copy()
        invalid_errors = stg_db.loc[invalid_mask, "validation_errors"]

        dup_count = int((err_dup_batch | err_dup_existing).sum())
        invalid_count = int(invalid_mask.sum())
        valid_count = int(len(valid_df))

        # Quarantine rejected records
        if invalid_count > 0:
            q_rows = []
            now_dt = datetime.now(timezone.utc)
            raw_dicts = invalid_raw[ALL_TX_COLUMNS].to_dict(orient="records")
            row_nums = invalid_raw["source_row_number"].tolist()
            tx_id_list = invalid_raw["transaction_id"].tolist()
            err_list = invalid_errors.tolist()

            for i in range(invalid_count):
                reason_str = err_list[i]
                severity = "CRITICAL" if ("DQ-001" in reason_str or "DQ-002" in reason_str or "DQ-003" in reason_str or "DQ-006" in reason_str or "DQ-009" in reason_str) else "HIGH"
                q_rows.append({
                    "quarantine_id": f"QRN-{uuid.uuid4().hex[:12].upper()}",
                    "ingestion_job_id": job_id,
                    "transaction_id": str(tx_id_list[i])[:64],
                    "source_file": path.name,
                    "source_row_number": int(row_nums[i]),
                    "raw_payload": json.dumps(raw_dicts[i], default=str),
                    "failure_reasons": reason_str,
                    "failed_rules": ",".join([part.split("[")[-1].rstrip("]") for part in reason_str.split(";") if "[" in part]),
                    "severity": severity,
                    "remediation_status": "OPEN",
                    "remediation_notes": "",
                    "quarantined_at": now_dt,
                    "updated_at": now_dt,
                })
            q_df = pd.DataFrame(q_rows)
            with duckdb_session() as conn:
                conn.register("tmp_q_df", q_df)
                conn.execute(f"INSERT INTO {gov_schema}.quarantined_records SELECT * FROM tmp_q_df")
                conn.unregister("tmp_q_df")

            db.add(LineageEvent(
                job_id=job_id,
                transformation_name="Quarantine Invalid Records",
                source_layer="Staging Dataset",
                source_table=f"{staging_schema}.transactions_staging",
                destination_layer="Governance Quarantine",
                destination_table=f"{gov_schema}.quarantined_records",
                records_in=records_received,
                records_out=invalid_count,
            ))

        # Load CURATED layer + Score Fraud Risk
        if valid_count > 0:
            cur_df = valid_df.drop(columns=["is_valid", "validation_errors", "processed_at"]).copy()
            cur_df["transaction_date"] = pd.to_datetime(cur_df["transaction_timestamp"]).dt.date
            cur_df = score_transactions_and_generate_alerts(db, cur_df)

            cols_order = [
                "transaction_id", "customer_id", "account_id", "card_token",
                "transaction_timestamp", "transaction_date", "transaction_amount",
                "currency", "merchant_id", "merchant_category", "transaction_type",
                "payment_method", "transaction_country", "transaction_city",
                "device_id", "transaction_status", "credit_limit",
                "outstanding_balance", "repayment_status", "customer_risk_category",
                "fraud_label", "ingestion_timestamp", "source_system",
                "ingestion_job_id", "fraud_risk_score", "fraud_risk_level",
                "risk_explanations", "ml_anomaly_score",
            ]
            cur_df = cur_df[cols_order]

            with duckdb_session() as conn:
                conn.register("tmp_cur_df", cur_df)
                conn.execute(f"INSERT OR IGNORE INTO {curated_schema}.transactions SELECT * FROM tmp_cur_df")
                conn.unregister("tmp_cur_df")

            db.add(LineageEvent(
                job_id=job_id,
                transformation_name="Curate & Fraud Score Transactions",
                source_layer="Staging Dataset",
                source_table=f"{staging_schema}.transactions_staging",
                destination_layer="Curated Dataset",
                destination_table=f"{curated_schema}.transactions",
                records_in=records_received,
                records_out=valid_count,
            ))

        # Refresh Analytics Marts
        refresh_analytics_marts()
        db.add(LineageEvent(
            job_id=job_id,
            transformation_name="Aggregate Analytics Marts",
            source_layer="Curated Dataset",
            source_table=f"{curated_schema}.transactions",
            destination_layer="Analytics Dataset",
            destination_table=f"{analytics_schema}.daily_transaction_metrics",
            records_in=valid_count,
            records_out=valid_count,
        ))

        # Run Data Quality Evaluation on staging batch
        run_quality_checks(db, dataset="transactions", triggered_by=triggered_by, job_id=job_id)

        # Update Catalog record counts
        _sync_catalog_counts(db)

        duration = round(time.perf_counter() - start_time, 3)
        job.records_processed = records_received
        job.valid_records = valid_count
        job.invalid_records = invalid_count
        job.duplicate_records = dup_count
        job.quarantined_records = invalid_count
        job.processing_duration_sec = duration
        job.status = "COMPLETED_WITH_QUARANTINE" if invalid_count > 0 else "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)

        record_audit_log(
            db,
            actor=triggered_by,
            actor_role="System",
            action="ETL_INGESTION_COMPLETED",
            resource_type="ingestion_job",
            resource_id=job_id,
            updated_value=f"file={path.name}, valid={valid_count}, quarantined={invalid_count}, duration={duration}s",
        )
        db.commit()

        return {
            "job_id": job_id,
            "status": job.status,
            "records_received": records_received,
            "valid_records": valid_count,
            "invalid_records": invalid_count,
            "duplicate_records": dup_count,
            "quarantined_records": invalid_count,
            "processing_duration_sec": duration,
        }

    except Exception as exc:
        logger.exception("ETL pipeline failed for job %s", job_id)
        duration = round(time.perf_counter() - start_time, 3)
        job.status = "FAILED"
        job.failure_reason = str(exc)
        job.processing_duration_sec = duration
        job.completed_at = datetime.now(timezone.utc)
        record_audit_log(
            db,
            actor=triggered_by,
            actor_role="System",
            action="ETL_INGESTION_FAILED",
            resource_type="ingestion_job",
            resource_id=job_id,
            updated_value=str(exc),
            execution_status="FAILED",
        )
        db.commit()
        raise


def refresh_analytics_marts() -> None:
    """Recompute analytical summary tables in finguard_analytics from curated data."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET
    analytics = settings.BIGQUERY_ANALYTICS_DATASET

    with duckdb_session() as conn:
        conn.execute(f"DELETE FROM {analytics}.daily_transaction_metrics")
        conn.execute(f"""
            INSERT INTO {analytics}.daily_transaction_metrics
            SELECT
                transaction_date,
                COUNT(*) AS total_transactions,
                ROUND(SUM(transaction_amount), 2) AS total_value,
                ROUND(AVG(transaction_amount), 2) AS avg_amount,
                SUM(CASE WHEN fraud_risk_score >= 50 THEN 1 ELSE 0 END) AS suspicious_count,
                SUM(CASE WHEN fraud_risk_score >= 75 THEN 1 ELSE 0 END) AS high_risk_count,
                SUM(CASE WHEN transaction_status IN ('FAILED', 'DECLINED') THEN 1 ELSE 0 END) AS failed_tx_count
            FROM {curated}.transactions
            GROUP BY transaction_date
            ORDER BY transaction_date
        """)

        conn.execute(f"DELETE FROM {analytics}.merchant_risk_summary")
        conn.execute(f"""
            INSERT INTO {analytics}.merchant_risk_summary
            SELECT
                merchant_category,
                COUNT(*) AS total_transactions,
                ROUND(SUM(transaction_amount), 2) AS total_value,
                ROUND(AVG(fraud_risk_score), 2) AS avg_fraud_score,
                SUM(CASE WHEN fraud_risk_score >= 50 THEN 1 ELSE 0 END) AS suspicious_count,
                ROUND(CAST(SUM(CASE WHEN fraud_risk_score >= 50 THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(COUNT(*), 0), 4) AS suspicious_rate
            FROM {curated}.transactions
            GROUP BY merchant_category
            ORDER BY suspicious_count DESC
        """)


def _sync_catalog_counts(db: Session) -> None:
    settings = get_settings()
    table_map = {
        f"{settings.BIGQUERY_RAW_DATASET}.transactions_raw": f"{settings.BIGQUERY_RAW_DATASET}.transactions_raw",
        f"{settings.BIGQUERY_STAGING_DATASET}.transactions_staging": f"{settings.BIGQUERY_STAGING_DATASET}.transactions_staging",
        f"{settings.BIGQUERY_CURATED_DATASET}.transactions": f"{settings.BIGQUERY_CURATED_DATASET}.transactions",
        f"{settings.BIGQUERY_CURATED_DATASET}.customers": f"{settings.BIGQUERY_CURATED_DATASET}.customers",
        f"{settings.BIGQUERY_CURATED_DATASET}.accounts": f"{settings.BIGQUERY_CURATED_DATASET}.accounts",
        f"{settings.BIGQUERY_CURATED_DATASET}.merchants": f"{settings.BIGQUERY_CURATED_DATASET}.merchants",
        f"{settings.BIGQUERY_GOVERNANCE_DATASET}.quarantined_records": f"{settings.BIGQUERY_GOVERNANCE_DATASET}.quarantined_records",
        f"{settings.BIGQUERY_ANALYTICS_DATASET}.daily_transaction_metrics": f"{settings.BIGQUERY_ANALYTICS_DATASET}.daily_transaction_metrics",
    }
    with duckdb_session() as conn:
        for catalog_table, duck_table in table_map.items():
            entry = db.query(DataCatalogEntry).filter(DataCatalogEntry.table_name == catalog_table).first()
            if entry:
                cnt = conn.execute(f"SELECT COUNT(*) FROM {duck_table}").fetchone()[0]
                entry.record_count = int(cnt)
                entry.last_updated = datetime.now(timezone.utc)
