"""Enterprise Data Governance routes: Catalog, Ownership, Glossary, Lineage, Policies, and Audit Trail."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import ROLE_ADMIN, ROLE_STEWARD, get_current_user, require_roles
from backend.app.governance.audit_service import record_audit_log
from backend.app.models.metadata import (
    AuditLog,
    BusinessGlossaryTerm,
    DataCatalogEntry,
    GovernancePolicy,
    LineageEvent,
    QualityCheckRun,
    User,
)
from backend.app.schemas.api import CatalogUpdateRequest, PolicyUpdateRequest

router = APIRouter(prefix="/api/governance", tags=["Data Governance"])


@router.get("/catalog")
def get_data_catalog(
    search: str | None = None,
    classification: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List cataloged datasets/tables with schema, ownership, classification, quality score, and retention."""
    query = db.query(DataCatalogEntry)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (DataCatalogEntry.table_name.ilike(like))
            | (DataCatalogEntry.description.ilike(like))
            | (DataCatalogEntry.dataset_name.ilike(like))
        )
    if classification:
        query = query.filter(DataCatalogEntry.data_classification == classification)

    entries = query.order_by(DataCatalogEntry.id.asc()).all()
    return [
        {
            "id": e.id,
            "dataset_name": e.dataset_name,
            "table_name": e.table_name,
            "description": e.description,
            "business_purpose": e.business_purpose,
            "business_owner": e.business_owner,
            "technical_owner": e.technical_owner,
            "data_steward": e.data_steward,
            "source_system": e.source_system,
            "schema": json.loads(e.schema_json or "[]"),
            "record_count": e.record_count,
            "data_classification": e.data_classification,
            "quality_score": e.quality_score,
            "retention_policy": e.retention_policy,
            "last_updated": e.last_updated.isoformat() if e.last_updated else None,
        }
        for e in entries
    ]


@router.patch("/catalog/{entry_id}")
def update_catalog_entry(
    entry_id: int,
    payload: CatalogUpdateRequest,
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_STEWARD)),
    db: Session = Depends(get_db),
):
    """Update ownership, classification, or retention policy on a catalog entry (Admin / Data Steward)."""
    entry = db.query(DataCatalogEntry).filter(DataCatalogEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found.")

    prev = f"owner={entry.business_owner}, steward={entry.data_steward}, class={entry.data_classification}"
    if payload.business_owner is not None:
        entry.business_owner = payload.business_owner
    if payload.technical_owner is not None:
        entry.technical_owner = payload.technical_owner
    if payload.data_steward is not None:
        entry.data_steward = payload.data_steward
    if payload.data_classification is not None:
        entry.data_classification = payload.data_classification
    if payload.retention_policy is not None:
        entry.retention_policy = payload.retention_policy
    entry.last_updated = datetime.now(timezone.utc)

    new_val = f"owner={entry.business_owner}, steward={entry.data_steward}, class={entry.data_classification}"
    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="CATALOG_METADATA_UPDATED",
        resource_type="data_catalog",
        resource_id=entry.table_name,
        previous_value=prev,
        updated_value=new_val,
    )
    db.commit()
    return {"id": entry.id, "table_name": entry.table_name, "data_classification": entry.data_classification}


@router.get("/glossary")
def get_business_glossary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return enterprise financial & governance business glossary terms."""
    terms = db.query(BusinessGlossaryTerm).order_by(BusinessGlossaryTerm.id.asc()).all()
    return [
        {
            "id": t.id,
            "term": t.term,
            "definition": t.definition,
            "formula_or_rule": t.formula_or_rule,
            "owner": t.owner,
            "related_datasets": t.related_datasets,
            "classification": t.classification,
        }
        for t in terms
    ]


@router.get("/lineage")
def get_data_lineage(
    limit: int = Query(default=40, ge=5, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return end-to-end architecture lineage pipeline stages plus recorded job lineage events."""
    events = db.query(LineageEvent).order_by(LineageEvent.executed_at.desc()).limit(limit).all()
    pipeline_stages = [
        {"id": "source", "label": "Source Files (CSV / JSON)", "layer": "Source", "dataset": "data/raw | GCS"},
        {"id": "raw", "label": "Raw Dataset", "layer": "Bronze", "dataset": "finguard_raw.transactions_raw"},
        {"id": "staging", "label": "Staging Dataset", "layer": "Silver-Stage", "dataset": "finguard_staging.transactions_staging"},
        {"id": "curated", "label": "Curated Dataset", "layer": "Silver-Clean", "dataset": "finguard_curated.transactions"},
        {"id": "quarantine", "label": "Quarantine Table", "layer": "Governance", "dataset": "finguard_governance.quarantined_records"},
        {"id": "analytics", "label": "Analytics Marts", "layer": "Gold", "dataset": "finguard_analytics.*"},
        {"id": "dashboard", "label": "FinGuard UI & Power BI", "layer": "Consumption", "dataset": "REST API / CSV / BigQuery"},
    ]
    return {
        "pipeline_stages": pipeline_stages,
        "edges": [
            {"from": "source", "to": "raw", "transformation": "Extract & SHA-256 Checksum"},
            {"from": "raw", "to": "staging", "transformation": "Standardize Schema, ISO Codes & Parse"},
            {"from": "staging", "to": "curated", "transformation": "Deduplicate, Validate & Fraud Score"},
            {"from": "staging", "to": "quarantine", "transformation": "Isolate Failed Validations"},
            {"from": "curated", "to": "analytics", "transformation": "Aggregate Daily & Merchant Marts"},
            {"from": "analytics", "to": "dashboard", "transformation": "Serve API & Power BI Views"},
        ],
        "recent_events": [
            {
                "id": e.id,
                "job_id": e.job_id,
                "transformation_name": e.transformation_name,
                "source_layer": e.source_layer,
                "source_table": e.source_table,
                "destination_layer": e.destination_layer,
                "destination_table": e.destination_table,
                "records_in": e.records_in,
                "records_out": e.records_out,
                "status": e.status,
                "executed_at": e.executed_at.isoformat() if e.executed_at else None,
            }
            for e in events
        ],
    }


@router.get("/policies")
def list_governance_policies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List enterprise governance policies with live evaluated compliance status."""
    policies = db.query(GovernancePolicy).order_by(GovernancePolicy.policy_id.asc()).all()
    latest_dq = db.query(QualityCheckRun).order_by(QualityCheckRun.executed_at.desc()).first()
    unowned_catalog = db.query(DataCatalogEntry).filter(
        (DataCatalogEntry.business_owner == "") | (DataCatalogEntry.data_steward == "")
    ).count()

    result = []
    for p in policies:
        status = "COMPLIANT"
        if not p.enabled:
            status = "DISABLED"
        elif p.policy_id == "POL-001" and latest_dq and latest_dq.overall_score < 95.0:
            status = "BREACHED"
        elif p.policy_id == "POL-003" and unowned_catalog > 0:
            status = "BREACHED"

        result.append({
            "policy_id": p.policy_id,
            "policy_name": p.policy_name,
            "category": p.category,
            "description": p.description,
            "threshold_rule": p.threshold_rule,
            "severity": p.severity,
            "enabled": p.enabled,
            "owner": p.owner,
            "compliance_status": status,
            "last_evaluated_at": p.last_evaluated_at.isoformat() if p.last_evaluated_at else None,
        })
    return result


@router.patch("/policies/{policy_id}")
def update_governance_policy(
    policy_id: str,
    payload: PolicyUpdateRequest,
    current_user: User = Depends(require_roles(ROLE_ADMIN)),
    db: Session = Depends(get_db),
):
    """Update or toggle a governance policy (Administrator only)."""
    policy = db.query(GovernancePolicy).filter(GovernancePolicy.policy_id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Governance policy not found.")

    prev = f"enabled={policy.enabled}, severity={policy.severity}, rule={policy.threshold_rule}"
    if payload.enabled is not None:
        policy.enabled = payload.enabled
    if payload.severity is not None:
        policy.severity = payload.severity
    if payload.threshold_rule is not None:
        policy.threshold_rule = payload.threshold_rule
    if payload.owner is not None:
        policy.owner = payload.owner
    policy.last_evaluated_at = datetime.now(timezone.utc)

    new_val = f"enabled={policy.enabled}, severity={policy.severity}, rule={policy.threshold_rule}"
    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="GOVERNANCE_POLICY_UPDATED",
        resource_type="governance_policy",
        resource_id=policy_id,
        previous_value=prev,
        updated_value=new_val,
    )
    db.commit()
    return {"policy_id": policy.policy_id, "enabled": policy.enabled, "severity": policy.severity}


@router.get("/audit-logs")
def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=5, le=200),
    search: str | None = None,
    action: str | None = None,
    actor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query append-only application audit logs with filtering and pagination."""
    query = db.query(AuditLog)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (AuditLog.resource_id.ilike(like))
            | (AuditLog.action.ilike(like))
            | (AuditLog.updated_value.ilike(like))
        )
    if action:
        query = query.filter(AuditLog.action == action)
    if actor:
        query = query.filter(AuditLog.actor == actor)
    if date_from:
        query = query.filter(AuditLog.timestamp >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(AuditLog.timestamp <= datetime.fromisoformat(f"{date_to}T23:59:59"))

    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "audit_disclaimer": "Application-level append-only audit records for demonstration; not a WORM-compliant regulatory ledger.",
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": log.id,
                "actor": log.actor,
                "actor_role": log.actor_role,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "previous_value": log.previous_value,
                "updated_value": log.updated_value,
                "execution_status": log.execution_status,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ],
    }
