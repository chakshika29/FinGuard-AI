"""CSV Reports Export and Power BI Dataset Export routes."""

import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import duckdb_session, get_db
from backend.app.core.security import get_current_user, mask_card_token
from backend.app.governance.audit_service import record_audit_log
from backend.app.models.metadata import AuditLog, QualityIssue, User
from scripts.export_bigquery_sandbox_csvs import export_sandbox_csvs

router = APIRouter(prefix="/api/reports", tags=["Reports & Exports"])


@router.get("/export")
def export_report_csv(
    report_type: str = Query(
        default="transactions",
        pattern="^(transactions|fraud_alerts|credit_risk|data_quality|quarantine|audit_logs|powerbi_bundle|bigquery_sandbox)$",
    ),
    limit: int = Query(default=50000, ge=1, le=250000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export analytical datasets or governance logs as downloadable CSV (and sync Sandbox/Power BI CSVs)."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET
    gov = settings.BIGQUERY_GOVERNANCE_DATASET
    analytics = settings.BIGQUERY_ANALYTICS_DATASET

    if report_type == "bigquery_sandbox":
        files = export_sandbox_csvs()
        record_audit_log(
            db,
            actor=current_user.username,
            actor_role=current_user.role,
            action="BIGQUERY_SANDBOX_CSVS_EXPORTED",
            resource_type="report",
            resource_id="bigquery_sandbox",
            updated_value=str(list(files.values())),
        )
        db.commit()
        return {
            "status": "exported",
            "directory": "data/bigquery_sandbox",
            "files": [f"{k}.csv" for k in files.keys()],
        }

    if report_type == "powerbi_bundle":
        # Materialize all 5 Power BI CSV datasets on disk and return summary JSON
        pbi_dir = settings.powerbi_dir
        with duckdb_session() as conn:
            conn.execute(f"SELECT * FROM {curated}.transactions LIMIT 100000").fetchdf().assign(
                card_token=lambda d: d["card_token"].map(mask_card_token)
            ).to_csv(pbi_dir / "fact_transactions.csv", index=False)

            conn.execute(f"SELECT * FROM {curated}.accounts").fetchdf().assign(
                card_token=lambda d: d["card_token"].map(mask_card_token)
            ).to_csv(pbi_dir / "dim_accounts_credit_risk.csv", index=False)

            conn.execute(f"SELECT * FROM {curated}.customers").fetchdf().to_csv(
                pbi_dir / "dim_customers.csv", index=False
            )
            conn.execute(f"SELECT * FROM {curated}.merchants").fetchdf().to_csv(
                pbi_dir / "dim_merchants.csv", index=False
            )
            conn.execute(f"SELECT * FROM {analytics}.daily_transaction_metrics").fetchdf().to_csv(
                pbi_dir / "mart_daily_metrics.csv", index=False
            )
            conn.execute(f"SELECT * FROM {gov}.quarantined_records").fetchdf().to_csv(
                pbi_dir / "fact_quarantined_records.csv", index=False
            )

        record_audit_log(
            db,
            actor=current_user.username,
            actor_role=current_user.role,
            action="POWERBI_DATASETS_EXPORTED",
            resource_type="report",
            resource_id="powerbi_bundle",
            updated_value=str(pbi_dir),
        )
        db.commit()
        return {
            "status": "exported",
            "directory": str(pbi_dir),
            "files": [
                "fact_transactions.csv",
                "dim_accounts_credit_risk.csv",
                "dim_customers.csv",
                "dim_merchants.csv",
                "mart_daily_metrics.csv",
                "fact_quarantined_records.csv",
            ],
        }

    buf = io.StringIO()
    if report_type == "transactions":
        with duckdb_session() as conn:
            df = conn.execute(f"SELECT * FROM {curated}.transactions ORDER BY transaction_timestamp DESC LIMIT ?", [limit]).fetchdf()
        if not df.empty and "card_token" in df.columns:
            df["card_token"] = df["card_token"].map(mask_card_token)
        df.to_csv(buf, index=False)
    elif report_type == "fraud_alerts":
        with duckdb_session() as conn:
            df = conn.execute(
                f"SELECT transaction_id, customer_id, merchant_id, merchant_category, transaction_amount, currency, transaction_country, transaction_timestamp, fraud_risk_score, fraud_risk_level, risk_explanations, ml_anomaly_score FROM {curated}.transactions WHERE fraud_risk_score >= 50 ORDER BY fraud_risk_score DESC LIMIT ?",
                [limit],
            ).fetchdf()
        df.to_csv(buf, index=False)
    elif report_type == "credit_risk":
        with duckdb_session() as conn:
            df = conn.execute(f"SELECT * FROM {curated}.accounts ORDER BY credit_risk_score DESC LIMIT ?", [limit]).fetchdf()
        if not df.empty and "card_token" in df.columns:
            df["card_token"] = df["card_token"].map(mask_card_token)
        df.to_csv(buf, index=False)
    elif report_type == "quarantine":
        with duckdb_session() as conn:
            df = conn.execute(f"SELECT * FROM {gov}.quarantined_records ORDER BY quarantined_at DESC LIMIT ?", [limit]).fetchdf()
        df.to_csv(buf, index=False)
    elif report_type == "data_quality":
        import pandas as pd
        issues = db.query(QualityIssue).order_by(QualityIssue.detected_at.desc()).limit(limit).all()
        df = pd.DataFrame([
            {
                "run_id": i.run_id,
                "rule_id": i.rule_id,
                "rule_name": i.rule_name,
                "dimension": i.dimension,
                "severity": i.severity,
                "failed_count": i.failed_count,
                "pass_rate": i.pass_rate,
                "status": i.status,
                "detected_at": i.detected_at.isoformat() if i.detected_at else "",
            }
            for i in issues
        ])
        df.to_csv(buf, index=False)
    elif report_type == "audit_logs":
        import pandas as pd
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        df = pd.DataFrame([
            {
                "id": log.id,
                "actor": log.actor,
                "actor_role": log.actor_role,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "previous_value": log.previous_value,
                "updated_value": log.updated_value,
                "status": log.execution_status,
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
            }
            for log in logs
        ])
        df.to_csv(buf, index=False)
    else:
        raise HTTPException(status_code=400, detail="Unsupported report_type")

    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="CSV_REPORT_EXPORTED",
        resource_type="report",
        resource_id=report_type,
    )
    db.commit()

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="finguard_{report_type}.csv"'},
    )
