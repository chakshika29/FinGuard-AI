"""Fraud Risk Analytics & Alert Investigation routes."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import duckdb_session, get_db
from backend.app.core.security import ROLE_ADMIN, ROLE_ANALYST, ROLE_STEWARD, get_current_user, mask_card_token, require_roles
from backend.app.fraud_detection.engine import train_and_evaluate_isolation_forest
from backend.app.governance.audit_service import record_audit_log
from backend.app.models.metadata import FraudAlert, MLModelEvaluation, User
from backend.app.schemas.api import FraudAlertUpdateRequest

router = APIRouter(prefix="/api/fraud", tags=["Fraud Risk Analytics"])


@router.get("/summary")
def fraud_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return fraud risk KPIs, severity breakdown, trends, and latest measured ML evaluation."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET
    analytics = settings.BIGQUERY_ANALYTICS_DATASET

    with duckdb_session() as conn:
        totals = conn.execute(f"""
            SELECT
                COUNT(*) AS total_tx,
                SUM(CASE WHEN fraud_risk_score >= 50 THEN 1 ELSE 0 END) AS suspicious_tx,
                SUM(CASE WHEN fraud_risk_score >= 75 THEN 1 ELSE 0 END) AS critical_tx,
                COALESCE(AVG(fraud_risk_score), 0) AS avg_score,
                COALESCE(SUM(CASE WHEN fraud_risk_score >= 50 THEN transaction_amount ELSE 0 END), 0) AS flagged_value
            FROM {curated}.transactions
        """).fetchone()

        by_level = conn.execute(f"""
            SELECT fraud_risk_level, COUNT(*) AS count, ROUND(SUM(transaction_amount), 2) AS total_value
            FROM {curated}.transactions
            GROUP BY fraud_risk_level
        """).fetchall()

        trend = conn.execute(f"""
            SELECT CAST(transaction_date AS VARCHAR), suspicious_count, high_risk_count, total_transactions
            FROM {analytics}.daily_transaction_metrics
            ORDER BY transaction_date ASC
            LIMIT 90
        """).fetchall()

        by_merchant = conn.execute(f"""
            SELECT merchant_category, total_transactions, suspicious_count, avg_fraud_score, ROUND(suspicious_rate * 100, 2)
            FROM {analytics}.merchant_risk_summary
            ORDER BY suspicious_count DESC
            LIMIT 10
        """).fetchall()

    total_tx = int(totals[0] or 0)
    suspicious_tx = int(totals[1] or 0)
    open_alerts = db.query(FraudAlert).filter(FraudAlert.investigation_status == "OPEN").count()
    latest_ml = db.query(MLModelEvaluation).order_by(MLModelEvaluation.evaluated_at.desc()).first()

    return {
        "disclaimer": "Suspicious transactions are risk indicators for analyst investigation, not confirmed fraud.",
        "total_transactions": total_tx,
        "suspicious_transactions": suspicious_tx,
        "suspicious_rate_pct": round((suspicious_tx / max(1, total_tx)) * 100.0, 2),
        "critical_risk_transactions": int(totals[2] or 0),
        "avg_fraud_risk_score": round(float(totals[3] or 0.0), 2),
        "flagged_exposure_value": round(float(totals[4] or 0.0), 2),
        "open_alerts": open_alerts,
        "risk_distribution": [
            {"level": r[0], "count": int(r[1]), "total_value": float(r[2] or 0)} for r in by_level
        ],
        "fraud_trends": [
            {
                "date": r[0],
                "suspicious_count": int(r[1]),
                "critical_count": int(r[2]),
                "total_transactions": int(r[3]),
            }
            for r in trend
        ],
        "merchant_risk_breakdown": [
            {
                "merchant_category": r[0],
                "total_transactions": int(r[1]),
                "suspicious_count": int(r[2]),
                "avg_score": float(r[3]),
                "suspicious_rate_pct": float(r[4] or 0),
            }
            for r in by_merchant
        ],
        "ml_evaluation": (
            {
                "model_name": latest_ml.model_name,
                "train_size": latest_ml.train_size,
                "test_size": latest_ml.test_size,
                "precision": latest_ml.precision,
                "recall": latest_ml.recall,
                "f1_score": latest_ml.f1_score,
                "false_positive_rate": latest_ml.false_positive_rate,
                "pr_auc": latest_ml.pr_auc,
                "confusion_matrix": json.loads(latest_ml.confusion_matrix_json or "{}"),
                "features": json.loads(latest_ml.feature_list_json or "[]"),
                "notes": latest_ml.notes,
                "evaluated_at": latest_ml.evaluated_at.isoformat() if latest_ml.evaluated_at else None,
            }
            if latest_ml
            else None
        ),
    }


@router.get("/alerts")
def list_fraud_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=5, le=200),
    risk_level: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List flagged suspicious transaction alerts with explainable reasons and investigation status."""
    query = db.query(FraudAlert)
    if risk_level:
        query = query.filter(FraudAlert.risk_level == risk_level)
    if status_filter:
        query = query.filter(FraudAlert.investigation_status == status_filter.upper())
    if search:
        like = f"%{search}%"
        query = query.filter(
            (FraudAlert.alert_id.ilike(like))
            | (FraudAlert.transaction_id.ilike(like))
            | (FraudAlert.customer_id.ilike(like))
            | (FraudAlert.merchant_category.ilike(like))
        )

    total = query.count()
    alerts = (
        query.order_by(FraudAlert.risk_score.desc(), FraudAlert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "alert_id": a.alert_id,
                "transaction_id": a.transaction_id,
                "customer_id": a.customer_id,
                "merchant_id": a.merchant_id,
                "merchant_category": a.merchant_category,
                "transaction_amount": a.transaction_amount,
                "transaction_country": a.transaction_country,
                "transaction_timestamp": a.transaction_timestamp,
                "risk_score": a.risk_score,
                "risk_level": a.risk_level,
                "explanations": json.loads(a.explanations_json or "[]"),
                "ml_anomaly_score": a.ml_anomaly_score,
                "investigation_status": a.investigation_status,
                "assigned_analyst": a.assigned_analyst,
                "analyst_notes": a.analyst_notes,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a in alerts
        ],
    }


@router.get("/transactions/{transaction_id}")
def get_fraud_transaction_analysis(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return detailed fraud risk breakdown for a specific transaction."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET
    with duckdb_session() as conn:
        row = conn.execute(
            f"""
            SELECT
                transaction_id, customer_id, account_id, card_token,
                CAST(transaction_timestamp AS VARCHAR), transaction_amount, currency,
                merchant_id, merchant_category, transaction_country, transaction_city,
                device_id, transaction_status, fraud_risk_score, fraud_risk_level,
                risk_explanations, ml_anomaly_score, fraud_label
            FROM {curated}.transactions
            WHERE transaction_id = ?
            """,
            [transaction_id],
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    alert = db.query(FraudAlert).filter(FraudAlert.transaction_id == transaction_id).first()
    return {
        "disclaimer": "Risk indicators only — not confirmed fraud.",
        "transaction_id": row[0],
        "customer_id": row[1],
        "account_id": row[2],
        "card_token_masked": mask_card_token(row[3]),
        "transaction_timestamp": row[4],
        "transaction_amount": float(row[5]),
        "currency": row[6],
        "merchant_id": row[7],
        "merchant_category": row[8],
        "transaction_country": row[9],
        "transaction_city": row[10],
        "device_id": row[11],
        "transaction_status": row[12],
        "fraud_risk_score": float(row[13] or 0.0),
        "fraud_risk_level": row[14],
        "risk_explanations": json.loads(row[15] or "[]"),
        "ml_anomaly_score": float(row[16] or 0.0),
        "synthetic_fraud_label": int(row[17] or 0),
        "alert": (
            {
                "alert_id": alert.alert_id,
                "investigation_status": alert.investigation_status,
                "analyst_notes": alert.analyst_notes,
            }
            if alert
            else None
        ),
    }


@router.patch("/alerts/{alert_id}")
def update_fraud_alert(
    alert_id: str,
    payload: FraudAlertUpdateRequest,
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ANALYST, ROLE_STEWARD)),
    db: Session = Depends(get_db),
):
    """Update fraud alert investigation status and analyst notes."""
    alert = db.query(FraudAlert).filter(FraudAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Fraud alert not found.")

    prev = f"status={alert.investigation_status}"
    alert.investigation_status = payload.investigation_status
    alert.analyst_notes = payload.analyst_notes
    alert.assigned_analyst = payload.assigned_analyst or current_user.username
    alert.updated_at = datetime.now(timezone.utc)

    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="FRAUD_ALERT_REVIEWED",
        resource_type="fraud_alert",
        resource_id=alert_id,
        previous_value=prev,
        updated_value=f"status={alert.investigation_status}",
    )
    db.commit()
    return {
        "alert_id": alert.alert_id,
        "investigation_status": alert.investigation_status,
        "assigned_analyst": alert.assigned_analyst,
    }


@router.post("/train-ml")
def run_isolation_forest_evaluation(
    contamination: float = Query(default=0.03, ge=0.005, le=0.25),
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_ANALYST)),
    db: Session = Depends(get_db),
):
    """Train IsolationForest without label leakage and compute held-out test metrics."""
    try:
        metrics = train_and_evaluate_isolation_forest(db, contamination=contamination)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="ML_ANOMALY_MODEL_EVALUATED",
        resource_type="ml_model",
        resource_id="IsolationForest",
        updated_value=f"precision={metrics['precision']}, recall={metrics['recall']}, f1={metrics['f1_score']}",
    )
    db.commit()
    return metrics
