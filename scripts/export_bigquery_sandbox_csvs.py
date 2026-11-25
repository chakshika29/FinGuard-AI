"""Export 5 clean CSV datasets from DuckDB for direct browser upload to BigQuery Sandbox.

Zero GCP billing, zero Cloud Storage bucket, and zero service account credentials required.
Each exported CSV stays well below BigQuery Console's 100 MB browser upload limit.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.core.config import get_settings  # noqa: E402
from backend.app.core.database import duckdb_session  # noqa: E402
from backend.app.core.security import mask_card_token  # noqa: E402


def export_sandbox_csvs(output_dir: str | Path | None = None) -> dict[str, str]:
    settings = get_settings()
    out_dir = Path(output_dir) if output_dir else (ROOT / "data" / "bigquery_sandbox")
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_s = settings.BIGQUERY_RAW_DATASET
    cur_s = settings.BIGQUERY_CURATED_DATASET
    gov_s = settings.BIGQUERY_GOVERNANCE_DATASET

    files: dict[str, str] = {}
    with duckdb_session() as conn:
        # 1. Raw transactions (preserve raw uncleaned values & masked card_token)
        raw_df = conn.execute(f"""
            SELECT
                transaction_id, customer_id, account_id, card_token,
                transaction_timestamp, transaction_amount, currency,
                merchant_id, merchant_category, transaction_type, payment_method,
                transaction_country, transaction_city, device_id, transaction_status,
                credit_limit, outstanding_balance, repayment_status,
                customer_risk_category, fraud_label, ingestion_timestamp,
                source_system, ingestion_job_id, source_file
            FROM {raw_s}.transactions_raw
        """).fetchdf()
        if not raw_df.empty:
            raw_df["card_token"] = raw_df["card_token"].map(mask_card_token)
        raw_path = out_dir / "raw_transactions.csv"
        raw_df.to_csv(raw_path, index=False)
        files["raw_transactions"] = str(raw_path)

        # 2. Cleaned curated transactions
        clean_df = conn.execute(f"""
            SELECT
                transaction_id, customer_id, account_id, card_token,
                CAST(transaction_timestamp AS VARCHAR) AS transaction_timestamp,
                CAST(transaction_date AS VARCHAR) AS transaction_date,
                transaction_amount, currency, merchant_id, merchant_category,
                transaction_type, payment_method, transaction_country,
                transaction_city, device_id, transaction_status,
                credit_limit, outstanding_balance, repayment_status,
                customer_risk_category, fraud_label, source_system,
                fraud_risk_score, fraud_risk_level
            FROM {cur_s}.transactions
        """).fetchdf()
        if not clean_df.empty:
            clean_df["card_token"] = clean_df["card_token"].map(mask_card_token)
        clean_path = out_dir / "cleaned_transactions.csv"
        clean_df.to_csv(clean_path, index=False)
        files["cleaned_transactions"] = str(clean_path)

        # 3. Quarantined records
        q_df = conn.execute(f"""
            SELECT
                quarantine_id, ingestion_job_id, transaction_id, source_file,
                source_row_number, failure_reasons, failed_rules, severity,
                remediation_status, CAST(quarantined_at AS VARCHAR) AS quarantined_at
            FROM {gov_s}.quarantined_records
        """).fetchdf()
        q_path = out_dir / "quarantined_records.csv"
        q_df.to_csv(q_path, index=False)
        files["quarantined_records"] = str(q_path)

        # 4. Fraud analytics dataset (scored transactions with explanations)
        fraud_df = conn.execute(f"""
            SELECT
                transaction_id, customer_id, merchant_id, merchant_category,
                CAST(transaction_timestamp AS VARCHAR) AS transaction_timestamp,
                CAST(transaction_date AS VARCHAR) AS transaction_date,
                transaction_amount, currency, transaction_country,
                transaction_status, device_id, fraud_risk_score,
                fraud_risk_level, risk_explanations, ml_anomaly_score,
                fraud_label AS synthetic_fraud_label
            FROM {cur_s}.transactions
        """).fetchdf()
        fraud_path = out_dir / "fraud_analytics.csv"
        fraud_df.to_csv(fraud_path, index=False)
        files["fraud_analytics"] = str(fraud_path)

        # 5. Credit risk analytics dataset (accounts + customer segment)
        credit_df = conn.execute(f"""
            SELECT
                a.account_id, a.customer_id, a.card_token,
                COALESCE(c.customer_segment, 'UNKNOWN') AS customer_segment,
                COALESCE(c.customer_risk_category, 'MEDIUM') AS customer_risk_category,
                COALESCE(c.home_country, 'US') AS home_country,
                a.credit_limit, a.outstanding_balance,
                a.credit_utilization_ratio, a.repayment_status,
                a.delinquency_days, a.account_status,
                a.credit_risk_score, a.credit_risk_tier
            FROM {cur_s}.accounts a
            LEFT JOIN {cur_s}.customers c ON a.customer_id = c.customer_id
        """).fetchdf()
        if not credit_df.empty:
            credit_df["card_token"] = credit_df["card_token"].map(mask_card_token)
        credit_path = out_dir / "credit_risk_analytics.csv"
        credit_df.to_csv(credit_path, index=False)
        files["credit_risk_analytics"] = str(credit_path)

    return files


if __name__ == "__main__":
    exported = export_sandbox_csvs()
    print("[OK] BigQuery Sandbox CSV files exported:")
    for name, path_str in exported.items():
        size_mb = Path(path_str).stat().st_size / (1024 * 1024)
        print(f"  - {name}: {path_str} ({size_mb:.2f} MB)")
