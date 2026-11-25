"""Dashboard summary, analytics trends, and system status routes."""

import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import duckdb_session, get_db
from backend.app.core.security import get_current_user
from backend.app.models.metadata import (
    GovernancePolicy,
    IngestionJob,
    QualityCheckRun,
    QualityIssue,
    QualityRule,
    User,
)
from backend.app.services.gcp_service import GCPIntegrationService

router = APIRouter(prefix="/api", tags=["Dashboard & Analytics"])


@router.get("/health")
def health_check():
    """Public health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "backend_mode": "bigquery" if settings.is_bigquery_mode else "local",
        "synthetic_data_notice": "All financial datasets are 100% synthetic.",
    }


@router.get("/system/status")
def system_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return runtime backend mode, DuckDB stats, and GCP configuration status."""
    settings = get_settings()
    gcp_status = GCPIntegrationService().check_connection()
    curated = settings.BIGQUERY_CURATED_DATASET
    with duckdb_session() as conn:
        tx_count = int(conn.execute(f"SELECT COUNT(*) FROM {curated}.transactions").fetchone()[0])
        cust_count = int(conn.execute(f"SELECT COUNT(*) FROM {curated}.customers").fetchone()[0])
        acct_count = int(conn.execute(f"SELECT COUNT(*) FROM {curated}.accounts").fetchone()[0])
        merch_count = int(conn.execute(f"SELECT COUNT(*) FROM {curated}.merchants").fetchone()[0])

    return {
        "app_name": settings.APP_NAME,
        "data_backend": "bigquery" if settings.is_bigquery_mode else "local",
        "local_engine": "DuckDB + SQLite Metadata",
        "gcp_status": gcp_status,
        "datasets": {
            "raw": settings.BIGQUERY_RAW_DATASET,
            "staging": settings.BIGQUERY_STAGING_DATASET,
            "curated": settings.BIGQUERY_CURATED_DATASET,
            "governance": settings.BIGQUERY_GOVERNANCE_DATASET,
            "analytics": settings.BIGQUERY_ANALYTICS_DATASET,
        },
        "warehouse_counts": {
            "transactions": tx_count,
            "customers": cust_count,
            "accounts": acct_count,
            "merchants": merch_count,
        },
        "current_user_role": current_user.role,
    }


@router.get("/dashboard/summary")
def dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return executive KPIs and chart data derived strictly from backend warehouse & metadata."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET
    analytics = settings.BIGQUERY_ANALYTICS_DATASET
    gov = settings.BIGQUERY_GOVERNANCE_DATASET

    with duckdb_session() as conn:
        tx_stats = conn.execute(f"""
            SELECT
                COUNT(*) AS total_tx,
                COALESCE(SUM(transaction_amount), 0) AS total_val,
                SUM(CASE WHEN fraud_risk_score >= 50 THEN 1 ELSE 0 END) AS suspicious_tx
            FROM {curated}.transactions
        """).fetchone()

        high_risk_accts = int(
            conn.execute(
                f"SELECT COUNT(*) FROM {curated}.accounts WHERE credit_risk_tier IN ('HIGH', 'CRITICAL') OR credit_utilization_ratio >= 0.75"
            ).fetchone()[0]
        )

        quarantined_cnt = int(
            conn.execute(f"SELECT COUNT(*) FROM {gov}.quarantined_records WHERE remediation_status = 'OPEN'").fetchone()[0]
        )

        volume_over_time = conn.execute(f"""
            SELECT
                CAST(transaction_date AS VARCHAR) AS date,
                total_transactions,
                total_value,
                suspicious_count
            FROM {analytics}.daily_transaction_metrics
            ORDER BY transaction_date ASC
            LIMIT 90
        """).fetchall()

        fraud_dist = conn.execute(f"""
            SELECT fraud_risk_level, COUNT(*) AS count
            FROM {curated}.transactions
            GROUP BY fraud_risk_level
        """).fetchall()

        amount_dist = conn.execute(f"""
            SELECT
                CASE
                    WHEN transaction_amount < 50 THEN '$0-$50'
                    WHEN transaction_amount < 200 THEN '$50-$200'
                    WHEN transaction_amount < 1000 THEN '$200-$1K'
                    WHEN transaction_amount < 5000 THEN '$1K-$5K'
                    ELSE '$5K+'
                END AS bucket,
                COUNT(*) AS count
            FROM {curated}.transactions
            GROUP BY bucket
        """).fetchall()

        risk_by_merchant = conn.execute(f"""
            SELECT merchant_category, total_transactions, avg_fraud_score, suspicious_count, ROUND(suspicious_rate * 100, 2)
            FROM {analytics}.merchant_risk_summary
            ORDER BY suspicious_count DESC
            LIMIT 10
        """).fetchall()

        util_dist = conn.execute(f"""
            SELECT
                CASE
                    WHEN credit_utilization_ratio < 0.25 THEN '0-25%'
                    WHEN credit_utilization_ratio < 0.50 THEN '25-50%'
                    WHEN credit_utilization_ratio < 0.75 THEN '50-75%'
                    WHEN credit_utilization_ratio < 0.90 THEN '75-90%'
                    ELSE '90%+'
                END AS bucket,
                COUNT(*) AS count
            FROM {curated}.accounts
            GROUP BY bucket
            ORDER BY bucket
        """).fetchall()

    latest_dq = db.query(QualityCheckRun).order_by(QualityCheckRun.executed_at.desc()).first()
    dq_history = db.query(QualityCheckRun).order_by(QualityCheckRun.executed_at.asc()).limit(20).all()
    active_rules = db.query(QualityRule).filter(QualityRule.enabled.is_(True)).count()
    latest_job = db.query(IngestionJob).order_by(IngestionJob.created_at.desc()).first()
    recent_issues = db.query(QualityIssue).order_by(QualityIssue.detected_at.desc()).limit(6).all()
    active_policies = db.query(GovernancePolicy).filter(GovernancePolicy.enabled.is_(True)).count()

    dimension_scores = json.loads(latest_dq.dimension_scores_json) if latest_dq else {}

    return {
        "backend_mode": "bigquery" if settings.is_bigquery_mode else "local",
        "kpis": {
            "total_transactions": int(tx_stats[0] or 0),
            "total_transaction_value": round(float(tx_stats[1] or 0.0), 2),
            "data_quality_score": float(latest_dq.overall_score) if latest_dq else 100.0,
            "suspicious_transactions": int(tx_stats[2] or 0),
            "high_risk_accounts": high_risk_accts,
            "active_governance_rules": active_rules,
            "active_policies": active_policies,
            "failed_validations": int(latest_dq.failed_validation_count) if latest_dq else 0,
            "open_quarantined": quarantined_cnt,
            "latest_ingestion_status": latest_job.status if latest_job else "NO_JOBS_YET",
            "latest_ingestion_file": latest_job.source_file if latest_job else None,
        },
        "charts": {
            "transaction_volume_over_time": [
                {
                    "date": r[0],
                    "transactions": int(r[1]),
                    "value": float(r[2]),
                    "suspicious": int(r[3]),
                }
                for r in volume_over_time
            ],
            "data_quality_trends": [
                {
                    "run_id": run.run_id,
                    "date": run.executed_at.strftime("%m-%d %H:%M") if run.executed_at else "",
                    "score": run.overall_score,
                    "failed": run.failed_validation_count,
                }
                for run in dq_history
            ],
            "fraud_risk_distribution": [{"level": r[0], "count": int(r[1])} for r in fraud_dist],
            "transaction_amount_distribution": [{"bucket": r[0], "count": int(r[1])} for r in amount_dist],
            "risk_by_merchant_category": [
                {
                    "category": r[0],
                    "transactions": int(r[1]),
                    "avg_score": float(r[2]),
                    "suspicious": int(r[3]),
                    "suspicious_rate_pct": float(r[4] or 0),
                }
                for r in risk_by_merchant
            ],
            "credit_utilization_distribution": [{"bucket": r[0], "count": int(r[1])} for r in util_dist],
            "quality_dimension_scores": [
                {"dimension": k, "score": v} for k, v in dimension_scores.items()
            ],
        },
        "recent_governance_violations": [
            {
                "rule_id": iss.rule_id,
                "rule_name": iss.rule_name,
                "dimension": iss.dimension,
                "severity": iss.severity,
                "failed_count": iss.failed_count,
                "pass_rate": iss.pass_rate,
                "detected_at": iss.detected_at.isoformat() if iss.detected_at else None,
            }
            for iss in recent_issues
        ],
    }


@router.get("/analytics/trends")
def analytics_trends(
    days: int = Query(default=60, ge=7, le=365),
    current_user: User = Depends(get_current_user),
):
    """Return time-series transaction, risk, and merchant analytics from DuckDB."""
    settings = get_settings()
    analytics = settings.BIGQUERY_ANALYTICS_DATASET
    curated = settings.BIGQUERY_CURATED_DATASET

    with duckdb_session() as conn:
        daily = conn.execute(f"""
            SELECT
                CAST(transaction_date AS VARCHAR) AS date,
                total_transactions,
                total_value,
                avg_amount,
                suspicious_count,
                high_risk_count,
                failed_tx_count
            FROM {analytics}.daily_transaction_metrics
            ORDER BY transaction_date DESC
            LIMIT ?
        """, [days]).fetchall()

        by_country = conn.execute(f"""
            SELECT
                transaction_country,
                COUNT(*) AS tx_count,
                ROUND(SUM(transaction_amount), 2) AS total_value,
                ROUND(AVG(fraud_risk_score), 2) AS avg_risk_score
            FROM {curated}.transactions
            GROUP BY transaction_country
            ORDER BY total_value DESC
            LIMIT 12
        """).fetchall()

    return {
        "daily_trends": [
            {
                "date": r[0],
                "total_transactions": int(r[1]),
                "total_value": float(r[2]),
                "avg_amount": float(r[3]),
                "suspicious_count": int(r[4]),
                "high_risk_count": int(r[5]),
                "failed_tx_count": int(r[6]),
            }
            for r in reversed(daily)
        ],
        "country_breakdown": [
            {
                "country": r[0],
                "tx_count": int(r[1]),
                "total_value": float(r[2]),
                "avg_risk_score": float(r[3]),
            }
            for r in by_country
        ],
    }
