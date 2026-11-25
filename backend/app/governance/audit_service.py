"""Append-only application audit trail service."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.metadata import AuditLog


def record_audit_log(
    db: Session,
    actor: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    previous_value: Any = None,
    updated_value: Any = None,
    execution_status: str = "SUCCESS",
) -> AuditLog:
    """Append an immutable-by-application-convention audit event."""
    entry = AuditLog(
        actor=actor,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        previous_value=str(previous_value) if previous_value is not None else None,
        updated_value=str(updated_value) if updated_value is not None else None,
        execution_status=execution_status,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.flush()
    return entry
