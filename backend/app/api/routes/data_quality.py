"""Data Quality Management routes: summary, rule CRUD, execution, issues, and quarantine remediation."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import duckdb_session, get_db
from backend.app.core.security import ROLE_ADMIN, ROLE_STEWARD, get_current_user, require_roles
from backend.app.data_quality.engine import run_quality_checks
from backend.app.governance.audit_service import record_audit_log
from backend.app.models.metadata import QualityCheckRun, QualityIssue, QualityRule, User
from backend.app.schemas.api import QualityRuleCreate, QualityRuleUpdate, QuarantineUpdateRequest

router = APIRouter(prefix="/api/data-quality", tags=["Data Quality"])


@router.get("/summary")
def quality_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return latest quality score, 7-dimension breakdown, rule pass rates, and history trend."""
    latest = db.query(QualityCheckRun).order_by(QualityCheckRun.executed_at.desc()).first()
    history = db.query(QualityCheckRun).order_by(QualityCheckRun.executed_at.asc()).limit(25).all()
    total_rules = db.query(QualityRule).count()
    enabled_rules = db.query(QualityRule).filter(QualityRule.enabled.is_(True)).count()

    settings = get_settings()
    gov = settings.BIGQUERY_GOVERNANCE_DATASET
    with duckdb_session() as conn:
        quarantine_counts = conn.execute(f"""
            SELECT remediation_status, COUNT(*)
            FROM {gov}.quarantined_records
            GROUP BY remediation_status
        """).fetchall()

    q_summary = {r[0]: int(r[1]) for r in quarantine_counts}
    return {
        "overall_score": latest.overall_score if latest else 100.0,
        "latest_run_id": latest.run_id if latest else None,
        "total_records_evaluated": latest.total_records_evaluated if latest else 0,
        "failed_validation_count": latest.failed_validation_count if latest else 0,
        "critical_issues_count": latest.critical_issues_count if latest else 0,
        "total_rules": total_rules,
        "enabled_rules": enabled_rules,
        "quarantine_summary": q_summary,
        "dimension_scores": json.loads(latest.dimension_scores_json) if latest else {},
        "rule_results": json.loads(latest.rule_results_json) if latest else [],
        "history": [
            {
                "run_id": h.run_id,
                "overall_score": h.overall_score,
                "failed_validation_count": h.failed_validation_count,
                "total_records_evaluated": h.total_records_evaluated,
                "executed_at": h.executed_at.isoformat() if h.executed_at else None,
            }
            for h in history
        ],
        "scoring_formula": "Weighted average of enabled rule pass rates: CRITICAL=4, HIGH=3, MEDIUM=2, LOW=1.",
    }


@router.get("/rules")
def list_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all configured data quality rules."""
    rules = db.query(QualityRule).order_by(QualityRule.rule_id.asc()).all()
    return [
        {
            "rule_id": r.rule_id,
            "rule_name": r.rule_name,
            "description": r.description,
            "dataset": r.dataset,
            "column_name": r.column_name,
            "dimension": r.dimension,
            "severity": r.severity,
            "threshold": r.threshold,
            "enabled": r.enabled,
            "owner": r.owner,
            "rule_type": r.rule_type,
            "rule_config": json.loads(r.rule_config or "{}"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_execution_date": r.last_execution_date.isoformat() if r.last_execution_date else None,
        }
        for r in rules
    ]


@router.post("/rules", status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: QualityRuleCreate,
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_STEWARD)),
    db: Session = Depends(get_db),
):
    """Create a new configurable data quality rule (Admin / Data Steward)."""
    rule_id = payload.rule_id or f"DQ-{uuid.uuid4().hex[:6].upper()}"
    if db.query(QualityRule).filter(QualityRule.rule_id == rule_id).first():
        raise HTTPException(status_code=400, detail=f"Rule '{rule_id}' already exists.")

    rule = QualityRule(
        rule_id=rule_id,
        rule_name=payload.rule_name,
        description=payload.description,
        dataset=payload.dataset,
        column_name=payload.column_name,
        dimension=payload.dimension,
        severity=payload.severity,
        threshold=payload.threshold,
        enabled=payload.enabled,
        owner=payload.owner,
        rule_type=payload.rule_type,
        rule_config=json.dumps(payload.rule_config),
    )
    db.add(rule)
    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="QUALITY_RULE_CREATED",
        resource_type="quality_rule",
        resource_id=rule_id,
        updated_value=f"{rule.rule_name} ({rule.dimension}, {rule.severity})",
    )
    db.commit()
    return {"rule_id": rule.rule_id, "rule_name": rule.rule_name, "enabled": rule.enabled}


@router.patch("/rules/{rule_id}")
def update_rule(
    rule_id: str,
    payload: QualityRuleUpdate,
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_STEWARD)),
    db: Session = Depends(get_db),
):
    """Update, enable, or disable an existing data quality rule (Admin / Data Steward)."""
    rule = db.query(QualityRule).filter(QualityRule.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Quality rule not found.")

    prev = f"enabled={rule.enabled}, threshold={rule.threshold}, severity={rule.severity}"
    if payload.rule_name is not None:
        rule.rule_name = payload.rule_name
    if payload.description is not None:
        rule.description = payload.description
    if payload.severity is not None:
        rule.severity = payload.severity
    if payload.threshold is not None:
        rule.threshold = payload.threshold
    if payload.enabled is not None:
        rule.enabled = payload.enabled
    if payload.owner is not None:
        rule.owner = payload.owner
    if payload.rule_config is not None:
        rule.rule_config = json.dumps(payload.rule_config)

    new_val = f"enabled={rule.enabled}, threshold={rule.threshold}, severity={rule.severity}"
    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="QUALITY_RULE_UPDATED",
        resource_type="quality_rule",
        resource_id=rule_id,
        previous_value=prev,
        updated_value=new_val,
    )
    db.commit()
    return {"rule_id": rule.rule_id, "enabled": rule.enabled, "threshold": rule.threshold, "severity": rule.severity}


@router.post("/run")
def trigger_quality_run(
    dataset: str = Query(default="transactions"),
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_STEWARD)),
    db: Session = Depends(get_db),
):
    """Manually trigger evaluation of all enabled data quality rules."""
    result = run_quality_checks(db, dataset=dataset, triggered_by=current_user.username)
    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="QUALITY_CHECKS_EXECUTED",
        resource_type="quality_run",
        resource_id=result["run_id"],
        updated_value=f"score={result['overall_score']}%, evaluated={result['total_records_evaluated']}",
    )
    db.commit()
    return result


@router.get("/issues")
def list_quality_issues(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List detected rule validation failures."""
    issues = db.query(QualityIssue).order_by(QualityIssue.detected_at.desc()).limit(limit).all()
    return [
        {
            "id": i.id,
            "run_id": i.run_id,
            "rule_id": i.rule_id,
            "rule_name": i.rule_name,
            "dataset": i.dataset,
            "column_name": i.column_name,
            "dimension": i.dimension,
            "severity": i.severity,
            "failed_count": i.failed_count,
            "pass_rate": i.pass_rate,
            "sample_values": json.loads(i.sample_values or "[]"),
            "status": i.status,
            "detected_at": i.detected_at.isoformat() if i.detected_at else None,
        }
        for i in issues
    ]


@router.get("/quarantine")
def list_quarantined_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=5, le=200),
    status_filter: str | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """List quarantined records preserved with failure reasons and remediation status."""
    settings = get_settings()
    gov = settings.BIGQUERY_GOVERNANCE_DATASET
    filters = ["1=1"]
    params: list[Any] = []
    if status_filter:
        filters.append("remediation_status = ?")
        params.append(status_filter.upper())
    if search:
        filters.append("(quarantine_id ILIKE ? OR transaction_id ILIKE ? OR failure_reasons ILIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    where_sql = " AND ".join(filters)
    offset = (page - 1) * page_size

    with duckdb_session() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM {gov}.quarantined_records WHERE {where_sql}", params).fetchone()[0])
        rows = conn.execute(
            f"""
            SELECT
                quarantine_id, ingestion_job_id, transaction_id, source_file,
                source_row_number, raw_payload, failure_reasons, failed_rules,
                severity, remediation_status, remediation_notes,
                CAST(quarantined_at AS VARCHAR)
            FROM {gov}.quarantined_records
            WHERE {where_sql}
            ORDER BY quarantined_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "quarantine_id": r[0],
                "ingestion_job_id": r[1],
                "transaction_id": r[2],
                "source_file": r[3],
                "source_row_number": int(r[4]),
                "raw_payload": json.loads(r[5] or "{}"),
                "failure_reasons": r[6],
                "failed_rules": r[7],
                "severity": r[8],
                "remediation_status": r[9],
                "remediation_notes": r[10],
                "quarantined_at": r[11],
            }
            for r in rows
        ],
    }


@router.patch("/quarantine/{quarantine_id}")
def update_quarantine_record(
    quarantine_id: str,
    payload: QuarantineUpdateRequest,
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_STEWARD)),
    db: Session = Depends(get_db),
):
    """Update remediation status and steward notes for a quarantined record."""
    settings = get_settings()
    gov = settings.BIGQUERY_GOVERNANCE_DATASET
    with duckdb_session() as conn:
        existing = conn.execute(
            f"SELECT remediation_status FROM {gov}.quarantined_records WHERE quarantine_id = ?",
            [quarantine_id],
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Quarantined record not found.")
        prev_status = existing[0]
        conn.execute(
            f"""
            UPDATE {gov}.quarantined_records
            SET remediation_status = ?, remediation_notes = ?, updated_at = ?
            WHERE quarantine_id = ?
            """,
            [payload.remediation_status, payload.remediation_notes, datetime.now(timezone.utc), quarantine_id],
        )

    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="QUARANTINE_REMEDIATION_UPDATED",
        resource_type="quarantined_record",
        resource_id=quarantine_id,
        previous_value=prev_status,
        updated_value=f"{payload.remediation_status}: {payload.remediation_notes}",
    )
    db.commit()
    return {"quarantine_id": quarantine_id, "remediation_status": payload.remediation_status}
