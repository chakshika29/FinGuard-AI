"""Bootstrap service to initialize databases, default demo accounts, quality rules, catalog, glossary, and policies."""

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import Base, engine, init_duckdb_warehouse
from backend.app.core.security import ROLE_ADMIN, ROLE_ANALYST, ROLE_STEWARD, hash_password
from backend.app.models.metadata import (
    BusinessGlossaryTerm,
    DataCatalogEntry,
    GovernancePolicy,
    QualityRule,
    User,
)


def init_all_databases(db: Session) -> None:
    """Create tables and seed initial governance, quality, and RBAC metadata."""
    Base.metadata.create_all(bind=engine)
    init_duckdb_warehouse()
    _seed_users(db)
    _seed_quality_rules(db)
    _seed_data_catalog(db)
    _seed_business_glossary(db)
    _seed_governance_policies(db)
    db.commit()


def _seed_users(db: Session) -> None:
    settings = get_settings()
    demo_users = [
        ("admin", "admin@finguard-demo.local", "Elena Vance (Admin)", ROLE_ADMIN, settings.DEMO_ADMIN_PASSWORD),
        ("steward", "steward@finguard-demo.local", "Marcus Chen (Data Steward)", ROLE_STEWARD, settings.DEMO_STEWARD_PASSWORD),
        ("analyst", "analyst@finguard-demo.local", "Priya Nair (Risk Analyst)", ROLE_ANALYST, settings.DEMO_ANALYST_PASSWORD),
    ]
    for username, email, full_name, role, password in demo_users:
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            db.add(
                User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role=role,
                    hashed_password=hash_password(password),
                    is_active=True,
                )
            )


def _seed_quality_rules(db: Session) -> None:
    default_rules = [
        {
            "rule_id": "DQ-001",
            "rule_name": "Mandatory Transaction ID",
            "description": "Every transaction record must contain a non-null, non-empty transaction_id.",
            "dataset": "transactions",
            "column_name": "transaction_id",
            "dimension": "Completeness",
            "severity": "CRITICAL",
            "threshold": 99.5,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "not_null",
            "rule_config": "{}",
        },
        {
            "rule_id": "DQ-002",
            "rule_name": "Mandatory Customer ID",
            "description": "Every transaction must reference a non-null customer_id.",
            "dataset": "transactions",
            "column_name": "customer_id",
            "dimension": "Completeness",
            "severity": "CRITICAL",
            "threshold": 99.0,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "not_null",
            "rule_config": "{}",
        },
        {
            "rule_id": "DQ-003",
            "rule_name": "Unique Transaction ID",
            "description": "Transaction IDs must be globally unique across ingested batches.",
            "dataset": "transactions",
            "column_name": "transaction_id",
            "dimension": "Uniqueness",
            "severity": "CRITICAL",
            "threshold": 99.5,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "unique",
            "rule_config": "{}",
        },
        {
            "rule_id": "DQ-004",
            "rule_name": "Valid ISO-4217 Currency Code",
            "description": "Currency must belong to approved ISO-4217 list (USD, EUR, GBP, CAD, INR, SGD, AUD, JPY).",
            "dataset": "transactions",
            "column_name": "currency",
            "dimension": "Validity",
            "severity": "HIGH",
            "threshold": 99.0,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "allowed_values",
            "rule_config": json.dumps({"values": ["USD", "EUR", "GBP", "CAD", "INR", "SGD", "AUD", "JPY"]}),
        },
        {
            "rule_id": "DQ-005",
            "rule_name": "Standardized ISO-3166 Country Code",
            "description": "Transaction country must conform to standardized 2-letter ISO country codes.",
            "dataset": "transactions",
            "column_name": "transaction_country",
            "dimension": "Consistency",
            "severity": "MEDIUM",
            "threshold": 98.0,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "allowed_values",
            "rule_config": json.dumps({"values": ["US", "GB", "CA", "IN", "SG", "DE", "FR", "AU", "JP", "AE", "BR", "MX"]}),
        },
        {
            "rule_id": "DQ-006",
            "rule_name": "Positive Transaction Amount Range",
            "description": "Transaction amount must be numeric, > 0.01, and <= 250,000.00.",
            "dataset": "transactions",
            "column_name": "transaction_amount",
            "dimension": "Accuracy",
            "severity": "CRITICAL",
            "threshold": 99.0,
            "owner": "Priya Nair (Risk Analyst)",
            "rule_type": "range",
            "rule_config": json.dumps({"min": 0.01, "max": 250000.0}),
        },
        {
            "rule_id": "DQ-007",
            "rule_name": "Valid Transaction Timestamp Format",
            "description": "Transaction timestamp must parse cleanly and not fall in the future.",
            "dataset": "transactions",
            "column_name": "transaction_timestamp",
            "dimension": "Validity",
            "severity": "HIGH",
            "threshold": 99.0,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "timestamp_valid",
            "rule_config": "{}",
        },
        {
            "rule_id": "DQ-008",
            "rule_name": "Data Freshness Within 365 Days",
            "description": "Transaction timestamps should be recent (within 365 days of ingestion) for timely risk scoring.",
            "dataset": "transactions",
            "column_name": "transaction_timestamp",
            "dimension": "Timeliness",
            "severity": "MEDIUM",
            "threshold": 98.0,
            "owner": "Elena Vance (Admin)",
            "rule_type": "timeliness",
            "rule_config": json.dumps({"max_age_days": 365}),
        },
        {
            "rule_id": "DQ-009",
            "rule_name": "Customer Referential Integrity",
            "description": "Every transaction customer_id must exist in curated customers master table.",
            "dataset": "transactions",
            "column_name": "customer_id",
            "dimension": "Referential Integrity",
            "severity": "CRITICAL",
            "threshold": 99.0,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "referential_integrity",
            "rule_config": json.dumps({"reference_table": "customers", "reference_column": "customer_id"}),
        },
        {
            "rule_id": "DQ-010",
            "rule_name": "Merchant Referential Integrity",
            "description": "Every transaction merchant_id must exist in curated merchants reference table.",
            "dataset": "transactions",
            "column_name": "merchant_id",
            "dimension": "Referential Integrity",
            "severity": "HIGH",
            "threshold": 99.0,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "referential_integrity",
            "rule_config": json.dumps({"reference_table": "merchants", "reference_column": "merchant_id"}),
        },
        {
            "rule_id": "DQ-011",
            "rule_name": "Valid Transaction Status",
            "description": "Transaction status must be one of APPROVED, DECLINED, PENDING, REVERSED, FAILED.",
            "dataset": "transactions",
            "column_name": "transaction_status",
            "dimension": "Consistency",
            "severity": "MEDIUM",
            "threshold": 99.5,
            "owner": "Marcus Chen (Data Steward)",
            "rule_type": "allowed_values",
            "rule_config": json.dumps({"values": ["APPROVED", "DECLINED", "PENDING", "REVERSED", "FAILED"]}),
        },
        {
            "rule_id": "DQ-012",
            "rule_name": "Non-Negative Credit Limit",
            "description": "Account credit_limit must be strictly positive (> 0).",
            "dataset": "transactions",
            "column_name": "credit_limit",
            "dimension": "Accuracy",
            "severity": "HIGH",
            "threshold": 99.5,
            "owner": "Priya Nair (Risk Analyst)",
            "rule_type": "range",
            "rule_config": json.dumps({"min": 1.0, "max": 1000000.0}),
        },
    ]

    for r in default_rules:
        if not db.query(QualityRule).filter(QualityRule.rule_id == r["rule_id"]).first():
            db.add(QualityRule(**r))


def _seed_data_catalog(db: Session) -> None:
    settings = get_settings()
    catalog_items = [
        {
            "dataset_name": settings.BIGQUERY_RAW_DATASET,
            "table_name": f"{settings.BIGQUERY_RAW_DATASET}.transactions_raw",
            "description": "Immutable landing zone storing unprocessed synthetic transaction payloads exactly as received from batch files.",
            "business_purpose": "Preserve auditability and raw replay capability before standardization and quality filtering.",
            "business_owner": "Head of Risk Data Engineering",
            "technical_owner": "Elena Vance (Admin)",
            "data_steward": "Marcus Chen (Data Steward)",
            "source_system": "CORE_CARD_GATEWAY / SYNTHETIC_GENERATOR",
            "schema_json": json.dumps([
                {"name": "transaction_id", "type": "STRING", "nullable": True},
                {"name": "customer_id", "type": "STRING", "nullable": True},
                {"name": "transaction_amount", "type": "STRING", "nullable": True},
                {"name": "currency", "type": "STRING", "nullable": True},
                {"name": "ingestion_job_id", "type": "STRING", "nullable": False},
                {"name": "file_checksum", "type": "STRING", "nullable": False},
            ]),
            "data_classification": "Restricted",
            "retention_policy": "7 Years (Synthetic Demo Retention)",
        },
        {
            "dataset_name": settings.BIGQUERY_STAGING_DATASET,
            "table_name": f"{settings.BIGQUERY_STAGING_DATASET}.transactions_staging",
            "description": "Standardized staging layer with normalized ISO country/currency codes, parsed timestamps, and row-level validation flags.",
            "business_purpose": "Decouple raw ingestion from curated consumption and track transformation validation outcomes.",
            "business_owner": "Enterprise Data Governance Office",
            "technical_owner": "Elena Vance (Admin)",
            "data_steward": "Marcus Chen (Data Steward)",
            "source_system": "ETL_STANDARDIZATION_ENGINE",
            "schema_json": json.dumps([
                {"name": "transaction_id", "type": "STRING", "nullable": True},
                {"name": "transaction_timestamp", "type": "TIMESTAMP", "nullable": True},
                {"name": "transaction_amount", "type": "FLOAT64", "nullable": True},
                {"name": "is_valid", "type": "BOOLEAN", "nullable": False},
                {"name": "validation_errors", "type": "STRING", "nullable": True},
            ]),
            "data_classification": "Confidential",
            "retention_policy": "90 Days Rolling Staging",
        },
        {
            "dataset_name": settings.BIGQUERY_CURATED_DATASET,
            "table_name": f"{settings.BIGQUERY_CURATED_DATASET}.transactions",
            "description": "Clean, deduplicated, referentially verified, and risk-scored synthetic transaction ledger partitioned by date.",
            "business_purpose": "Single source of truth for fraud risk analytics, regulatory reporting, and executive BI dashboards.",
            "business_owner": "Chief Risk Officer (Demo)",
            "technical_owner": "Elena Vance (Admin)",
            "data_steward": "Marcus Chen (Data Steward)",
            "source_system": "FINGUARD_CURATION_PIPELINE",
            "schema_json": json.dumps([
                {"name": "transaction_id", "type": "STRING", "nullable": False},
                {"name": "customer_id", "type": "STRING", "nullable": False},
                {"name": "transaction_date", "type": "DATE", "nullable": False},
                {"name": "transaction_amount", "type": "FLOAT64", "nullable": False},
                {"name": "fraud_risk_score", "type": "FLOAT64", "nullable": False},
                {"name": "fraud_risk_level", "type": "STRING", "nullable": False},
            ]),
            "data_classification": "Confidential",
            "retention_policy": "7 Years Curated Ledger",
        },
        {
            "dataset_name": settings.BIGQUERY_CURATED_DATASET,
            "table_name": f"{settings.BIGQUERY_CURATED_DATASET}.customers",
            "description": "Synthetic customer master profiles with risk tier, segment, and home geography.",
            "business_purpose": "Enable customer-level behavioral baselines, credit segmentation, and referential checks.",
            "business_owner": "Credit Risk Analytics Team",
            "technical_owner": "Elena Vance (Admin)",
            "data_steward": "Marcus Chen (Data Steward)",
            "source_system": "CRM_SYNTHETIC_MASTER",
            "schema_json": json.dumps([
                {"name": "customer_id", "type": "STRING", "nullable": False},
                {"name": "customer_segment", "type": "STRING", "nullable": False},
                {"name": "customer_risk_category", "type": "STRING", "nullable": False},
                {"name": "home_country", "type": "STRING", "nullable": False},
            ]),
            "data_classification": "Restricted",
            "retention_policy": "7 Years Customer Master",
        },
        {
            "dataset_name": settings.BIGQUERY_CURATED_DATASET,
            "table_name": f"{settings.BIGQUERY_CURATED_DATASET}.accounts",
            "description": "Synthetic revolving credit accounts with credit limits, balances, utilization, and delinquency flags.",
            "business_purpose": "Power portfolio credit risk exposure, utilization monitoring, and delinquency tracking.",
            "business_owner": "Credit Risk Analytics Team",
            "technical_owner": "Elena Vance (Admin)",
            "data_steward": "Priya Nair (Risk Analyst)",
            "source_system": "CORE_CREDIT_SYSTEM",
            "schema_json": json.dumps([
                {"name": "account_id", "type": "STRING", "nullable": False},
                {"name": "credit_limit", "type": "FLOAT64", "nullable": False},
                {"name": "outstanding_balance", "type": "FLOAT64", "nullable": False},
                {"name": "credit_utilization_ratio", "type": "FLOAT64", "nullable": False},
                {"name": "repayment_status", "type": "STRING", "nullable": False},
            ]),
            "data_classification": "Confidential",
            "retention_policy": "7 Years Credit Records",
        },
        {
            "dataset_name": settings.BIGQUERY_CURATED_DATASET,
            "table_name": f"{settings.BIGQUERY_CURATED_DATASET}.merchants",
            "description": "Synthetic merchant reference directory with MCC category and merchant risk tier.",
            "business_purpose": "Support merchant category risk aggregation and referential integrity checks.",
            "business_owner": "Merchant Acquiring Ops",
            "technical_owner": "Elena Vance (Admin)",
            "data_steward": "Marcus Chen (Data Steward)",
            "source_system": "MERCHANT_REGISTRY",
            "schema_json": json.dumps([
                {"name": "merchant_id", "type": "STRING", "nullable": False},
                {"name": "merchant_name", "type": "STRING", "nullable": False},
                {"name": "merchant_category", "type": "STRING", "nullable": False},
                {"name": "merchant_risk_tier", "type": "STRING", "nullable": False},
            ]),
            "data_classification": "Internal",
            "retention_policy": "5 Years Reference Data",
        },
        {
            "dataset_name": settings.BIGQUERY_GOVERNANCE_DATASET,
            "table_name": f"{settings.BIGQUERY_GOVERNANCE_DATASET}.quarantined_records",
            "description": "Repository of rejected/failed transaction records preserved with failure reasons and remediation status.",
            "business_purpose": "Prevent silent data loss while enabling steward root-cause analysis and remediation.",
            "business_owner": "Enterprise Data Governance Office",
            "technical_owner": "Elena Vance (Admin)",
            "data_steward": "Marcus Chen (Data Steward)",
            "source_system": "DATA_QUALITY_ENGINE",
            "schema_json": json.dumps([
                {"name": "quarantine_id", "type": "STRING", "nullable": False},
                {"name": "transaction_id", "type": "STRING", "nullable": True},
                {"name": "failure_reasons", "type": "STRING", "nullable": False},
                {"name": "remediation_status", "type": "STRING", "nullable": False},
            ]),
            "data_classification": "Confidential",
            "retention_policy": "3 Years Remediation Archive",
        },
        {
            "dataset_name": settings.BIGQUERY_ANALYTICS_DATASET,
            "table_name": f"{settings.BIGQUERY_ANALYTICS_DATASET}.daily_transaction_metrics",
            "description": "Pre-aggregated daily KPIs for executive reporting and Power BI DirectQuery/CSV consumption.",
            "business_purpose": "Accelerate BI dashboards and trend reporting across transaction volume and risk rates.",
            "business_owner": "Enterprise BI & Analytics",
            "technical_owner": "Elena Vance (Admin)",
            "data_steward": "Priya Nair (Risk Analyst)",
            "source_system": "ANALYTICS_MART_BUILDER",
            "schema_json": json.dumps([
                {"name": "transaction_date", "type": "DATE", "nullable": False},
                {"name": "total_transactions", "type": "INT64", "nullable": False},
                {"name": "total_value", "type": "FLOAT64", "nullable": False},
                {"name": "suspicious_count", "type": "INT64", "nullable": False},
            ]),
            "data_classification": "Internal",
            "retention_policy": "5 Years Analytical Mart",
        },
    ]

    for item in catalog_items:
        if not db.query(DataCatalogEntry).filter(DataCatalogEntry.table_name == item["table_name"]).first():
            db.add(DataCatalogEntry(**item, last_updated=datetime.now(timezone.utc)))


def _seed_business_glossary(db: Session) -> None:
    terms = [
        {
            "term": "Transaction Amount",
            "definition": "The monetary value of a single synthetic payment authorization or settlement event in its billed currency.",
            "formula_or_rule": "Must be > 0.01 and <= 250,000.00 in curated layer.",
            "owner": "Priya Nair (Risk Analyst)",
            "related_datasets": "finguard_curated.transactions, finguard_analytics.daily_transaction_metrics",
            "classification": "Confidential",
        },
        {
            "term": "Credit Utilization",
            "definition": "The ratio of an account's current outstanding balance to its approved total credit limit.",
            "formula_or_rule": "outstanding_balance / credit_limit (expressed as 0.00-1.00+ or percentage).",
            "owner": "Priya Nair (Risk Analyst)",
            "related_datasets": "finguard_curated.accounts",
            "classification": "Confidential",
        },
        {
            "term": "Fraud Risk Score",
            "definition": "An explainable composite indicator (0-100) quantifying anomalous transaction behavior across amount, velocity, geography, merchant, and device rules.",
            "formula_or_rule": "Weighted sum of triggered risk rules capped at 100; >= 50 High Risk, >= 75 Critical Risk.",
            "owner": "Priya Nair (Risk Analyst)",
            "related_datasets": "finguard_curated.transactions, fraud_alerts",
            "classification": "Confidential",
        },
        {
            "term": "Data Quality Score",
            "definition": "Weighted composite percentage (0-100%) measuring dataset conformance across Completeness, Accuracy, Consistency, Uniqueness, Validity, Timeliness, and Referential Integrity.",
            "formula_or_rule": "Sum(rule_pass_rate * severity_weight) / Sum(severity_weight).",
            "owner": "Marcus Chen (Data Steward)",
            "related_datasets": "finguard_governance.quality_check_runs",
            "classification": "Internal",
        },
        {
            "term": "Outstanding Balance",
            "definition": "Total unpaid synthetic revolving credit balance currently owed on an account.",
            "formula_or_rule": "Non-negative monetary amount tracked per account_id.",
            "owner": "Credit Risk Analytics Team",
            "related_datasets": "finguard_curated.accounts",
            "classification": "Confidential",
        },
        {
            "term": "Delinquency",
            "definition": "Account status where minimum payment obligations are past due (30+, 60+, 90+ days, or Default).",
            "formula_or_rule": "delinquency_days > 0 OR repayment_status IN ('PAST_DUE_30', 'PAST_DUE_60', 'PAST_DUE_90', 'DEFAULT').",
            "owner": "Credit Risk Analytics Team",
            "related_datasets": "finguard_curated.accounts",
            "classification": "Confidential",
        },
        {
            "term": "Suspicious Transaction",
            "definition": "A transaction flagged by rule-based or anomaly-detection logic as exhibiting elevated risk indicators requiring analyst review (not confirmed fraud).",
            "formula_or_rule": "fraud_risk_score >= 50.0 (High or Critical Risk).",
            "owner": "Priya Nair (Risk Analyst)",
            "related_datasets": "finguard_curated.transactions, fraud_alerts",
            "classification": "Confidential",
        },
        {
            "term": "Data Lineage",
            "definition": "End-to-end traceability documenting how data moves and transforms from source files through raw, staging, curated, and analytics layers to BI dashboards.",
            "formula_or_rule": "Tracked via job_id, source_table, destination_table, transformation_name, and record counts.",
            "owner": "Marcus Chen (Data Steward)",
            "related_datasets": "finguard_governance.lineage_events",
            "classification": "Internal",
        },
    ]
    for t in terms:
        if not db.query(BusinessGlossaryTerm).filter(BusinessGlossaryTerm.term == t["term"]).first():
            db.add(BusinessGlossaryTerm(**t))


def _seed_governance_policies(db: Session) -> None:
    policies = [
        {
            "policy_id": "POL-001",
            "policy_name": "Minimum Overall Data Quality Threshold",
            "category": "Quality Thresholds",
            "description": "Curated transaction datasets must maintain an overall Data Quality Score >= 95.0% after ETL curation.",
            "threshold_rule": "overall_quality_score >= 95.0",
            "severity": "CRITICAL",
            "owner": "Marcus Chen (Data Steward)",
        },
        {
            "policy_id": "POL-002",
            "policy_name": "Zero Silent Record Drops (Quarantine Mandate)",
            "category": "Mandatory Field Validation",
            "description": "All records failing ingestion validation must be preserved in finguard_governance.quarantined_records with failure reasons.",
            "threshold_rule": "quarantined_preserved == invalid_records",
            "severity": "CRITICAL",
            "owner": "Marcus Chen (Data Steward)",
        },
        {
            "policy_id": "POL-003",
            "policy_name": "Dataset Ownership Assignment",
            "category": "Data Ownership",
            "description": "Every cataloged table must have assigned Business Owner, Technical Owner, and Data Steward.",
            "threshold_rule": "all_catalog_entries_have_owners == true",
            "severity": "HIGH",
            "owner": "Elena Vance (Admin)",
        },
        {
            "policy_id": "POL-004",
            "policy_name": "Sensitive Data Classification & Masking",
            "category": "Sensitive Data Classification",
            "description": "Card tokens and customer identifiers must be classified Restricted/Confidential and masked in standard API/UI views.",
            "threshold_rule": "card_token_masked == true",
            "severity": "CRITICAL",
            "owner": "Elena Vance (Admin)",
        },
        {
            "policy_id": "POL-005",
            "policy_name": "Curated Ledger Retention Window",
            "category": "Data Retention",
            "description": "Curated financial transaction records carry a 7-year retention policy; staging records expire after 90 days.",
            "threshold_rule": "retention_policy_defined == true",
            "severity": "MEDIUM",
            "owner": "Elena Vance (Admin)",
        },
        {
            "policy_id": "POL-006",
            "policy_name": "Data Freshness SLA",
            "category": "Data Freshness",
            "description": "Analytics marts must be refreshed within 24 hours of latest curated ingestion job.",
            "threshold_rule": "analytics_lag_hours <= 24",
            "severity": "HIGH",
            "owner": "Marcus Chen (Data Steward)",
        },
        {
            "policy_id": "POL-007",
            "policy_name": "Role-Based Access Enforcement",
            "category": "Access Control",
            "description": "Only Administrator and Data Steward roles may mutate quality rules, catalog metadata, or quarantine remediation status.",
            "threshold_rule": "rbac_enforced == true",
            "severity": "CRITICAL",
            "owner": "Elena Vance (Admin)",
        },
    ]
    for p in policies:
        if not db.query(GovernancePolicy).filter(GovernancePolicy.policy_id == p["policy_id"]).first():
            db.add(GovernancePolicy(**p, last_evaluated_at=datetime.now(timezone.utc)))
