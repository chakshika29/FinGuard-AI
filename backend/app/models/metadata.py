"""SQLAlchemy ORM models for operational metadata, governance, quality rules, and alerts."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_file: Mapped[str] = mapped_column(String(256), nullable=False)
    file_format: Mapped[str] = mapped_column(String(16), nullable=False)
    file_checksum: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    valid_records: Mapped[int] = mapped_column(Integer, default=0)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0)
    quarantined_records: Mapped[int] = mapped_column(Integer, default=0)
    processing_duration_sec: Mapped[float] = mapped_column(Float, default=0.0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotent_skip: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_by: Mapped[str] = mapped_column(String(64), default="system")
    backend_target: Mapped[str] = mapped_column(String(32), default="local")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QualityRule(Base):
    __tablename__ = "quality_rules"

    rule_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    column_name: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold: Mapped[float] = mapped_column(Float, default=99.0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_config: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_execution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QualityCheckRun(Base):
    __tablename__ = "quality_check_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    total_records_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    failed_validation_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    dimension_scores_json: Mapped[str] = mapped_column(Text, default="{}")
    rule_results_json: Mapped[str] = mapped_column(Text, default="[]")
    triggered_by: Mapped[str] = mapped_column(String(64), default="system")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class QualityIssue(Base):
    __tablename__ = "quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset: Mapped[str] = mapped_column(String(64), nullable=False)
    column_name: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, default=100.0)
    sample_values: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DataCatalogEntry(Base):
    __tablename__ = "data_catalog_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_name: Mapped[str] = mapped_column(String(64), nullable=False)
    table_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_purpose: Mapped[str] = mapped_column(Text, nullable=False)
    business_owner: Mapped[str] = mapped_column(String(64), nullable=False)
    technical_owner: Mapped[str] = mapped_column(String(64), nullable=False)
    data_steward: Mapped[str] = mapped_column(String(64), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_json: Mapped[str] = mapped_column(Text, default="[]")
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    data_classification: Mapped[str] = mapped_column(String(32), default="Confidential")
    quality_score: Mapped[float] = mapped_column(Float, default=100.0)
    retention_policy: Mapped[str] = mapped_column(String(128), default="7 Years (Synthetic Demo)")
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class BusinessGlossaryTerm(Base):
    __tablename__ = "business_glossary_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    formula_or_rule: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    related_datasets: Mapped[str] = mapped_column(String(256), default="")
    classification: Mapped[str] = mapped_column(String(32), default="Internal")


class LineageEvent(Base):
    __tablename__ = "lineage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    transformation_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_layer: Mapped[str] = mapped_column(String(64), nullable=False)
    source_table: Mapped[str] = mapped_column(String(128), nullable=False)
    destination_layer: Mapped[str] = mapped_column(String(64), nullable=False)
    destination_table: Mapped[str] = mapped_column(String(128), nullable=False)
    records_in: Mapped[int] = mapped_column(Integer, default=0)
    records_out: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GovernancePolicy(Base):
    __tablename__ = "governance_policies"

    policy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    threshold_rule: Mapped[str] = mapped_column(String(256), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="HIGH")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(64), nullable=False)
    compliance_status: Mapped[str] = mapped_column(String(32), default="COMPLIANT")
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """Append-only application-level audit trail (see SECURITY.md for immutability scope)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    merchant_category: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_amount: Mapped[float] = mapped_column(Float, nullable=False)
    transaction_country: Mapped[str] = mapped_column(String(32), nullable=False)
    transaction_timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    explanations_json: Mapped[str] = mapped_column(Text, default="[]")
    ml_anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    investigation_status: Mapped[str] = mapped_column(String(32), default="OPEN")
    assigned_analyst: Mapped[str | None] = mapped_column(String(64), nullable=True)
    analyst_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MLModelEvaluation(Base):
    __tablename__ = "ml_model_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    train_size: Mapped[int] = mapped_column(Integer, default=0)
    test_size: Mapped[int] = mapped_column(Integer, default=0)
    precision: Mapped[float] = mapped_column(Float, default=0.0)
    recall: Mapped[float] = mapped_column(Float, default=0.0)
    f1_score: Mapped[float] = mapped_column(Float, default=0.0)
    false_positive_rate: Mapped[float] = mapped_column(Float, default=0.0)
    pr_auc: Mapped[float] = mapped_column(Float, default=0.0)
    confusion_matrix_json: Mapped[str] = mapped_column(Text, default="{}")
    feature_list_json: Mapped[str] = mapped_column(Text, default="[]")
    notes: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
