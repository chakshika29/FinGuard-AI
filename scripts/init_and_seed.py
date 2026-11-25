"""Initialize databases, generate initial 100,000-record synthetic dataset, run ETL + IsolationForest, and export Power BI CSVs."""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.core.bootstrap import init_all_databases  # noqa: E402
from backend.app.core.config import get_settings  # noqa: E402
from backend.app.core.database import SessionLocal, duckdb_session  # noqa: E402
from backend.app.core.security import mask_card_token  # noqa: E402
from backend.app.fraud_detection.engine import train_and_evaluate_isolation_forest  # noqa: E402
from backend.app.pipelines.etl import run_etl_pipeline  # noqa: E402
from backend.app.pipelines.generator import generate_synthetic_dataset  # noqa: E402


def main(records: int = 100000) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        print("[1/4] Initializing SQLite metadata & DuckDB 5-layer warehouse...")
        init_all_databases(db)

        print(f"[2/4] Generating {records:,} synthetic financial records (seed=42)...")
        t0 = time.perf_counter()
        gen = generate_synthetic_dataset(
            num_records=records,
            seed=42,
            output_dir=settings.sample_dir,
            quality_issue_rate=0.03,
            fraud_rate=0.025,
            file_format="csv",
            prefix="finguard_seed",
        )
        print(f"      Generated in {time.perf_counter() - t0:.2f}s | Fraud={gen['manifest']['synthetic_fraud_count']} | InjectedDQ={gen['manifest']['total_injected_issues']}")

        print("[3/4] Running Enterprise ETL pipeline (Extract -> Standardize -> Quarantine -> Curate -> Score)...")
        etl_res = run_etl_pipeline(
            db=db,
            job_id="JOB-BOOTSTRAP-100K",
            file_path=gen["transactions_file"],
            triggered_by="admin",
            customers_file=gen["customers_file"],
            accounts_file=gen["accounts_file"],
            merchants_file=gen["merchants_file"],
        )
        print(f"      ETL Result: {etl_res}")

        print("[4/4] Training & evaluating IsolationForest ML model (zero label leakage)...")
        ml_res = train_and_evaluate_isolation_forest(db)
        print(f"      ML Metrics: Precision={ml_res['precision']}, Recall={ml_res['recall']}, F1={ml_res['f1_score']}, PR-AUC={ml_res['pr_auc']}, FPR={ml_res['false_positive_rate']}")

        # Export Power BI CSV datasets
        pbi_dir = settings.powerbi_dir
        curated = settings.BIGQUERY_CURATED_DATASET
        analytics = settings.BIGQUERY_ANALYTICS_DATASET
        gov = settings.BIGQUERY_GOVERNANCE_DATASET
        with duckdb_session() as conn:
            conn.execute(f"SELECT * FROM {curated}.transactions").fetchdf().assign(
                card_token=lambda d: d["card_token"].map(mask_card_token)
            ).to_csv(pbi_dir / "fact_transactions.csv", index=False)
            conn.execute(f"SELECT * FROM {curated}.accounts").fetchdf().assign(
                card_token=lambda d: d["card_token"].map(mask_card_token)
            ).to_csv(pbi_dir / "dim_accounts_credit_risk.csv", index=False)
            conn.execute(f"SELECT * FROM {curated}.customers").fetchdf().to_csv(pbi_dir / "dim_customers.csv", index=False)
            conn.execute(f"SELECT * FROM {curated}.merchants").fetchdf().to_csv(pbi_dir / "dim_merchants.csv", index=False)
            conn.execute(f"SELECT * FROM {analytics}.daily_transaction_metrics").fetchdf().to_csv(pbi_dir / "mart_daily_metrics.csv", index=False)
            conn.execute(f"SELECT * FROM {gov}.quarantined_records").fetchdf().to_csv(pbi_dir / "fact_quarantined_records.csv", index=False)
        print(f"[DONE] Power BI CSV datasets exported to {pbi_dir}")
    finally:
        db.close()


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    main(count)
