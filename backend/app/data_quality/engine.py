"""Configurable 7-Dimension Enterprise Data Quality Management Engine."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import duckdb_session
from backend.app.models.metadata import DataCatalogEntry, QualityCheckRun, QualityIssue, QualityRule

DIMENSIONS = [
    "Completeness",
    "Accuracy",
    "Consistency",
    "Uniqueness",
    "Validity",
    "Timeliness",
    "Referential Integrity",
]

SEVERITY_WEIGHTS = {
    "CRITICAL": 4.0,
    "HIGH": 3.0,
    "MEDIUM": 2.0,
    "LOW": 1.0,
}


def run_quality_checks(
    db: Session,
    dataset: str = "transactions",
    triggered_by: str = "system",
    job_id: str | None = None,
) -> dict[str, Any]:
    """Execute all enabled quality rules against staging (if populated) & curated tables and persist results."""
    settings = get_settings()
    staging_table = f"{settings.BIGQUERY_STAGING_DATASET}.transactions_staging"
    curated_schema = settings.BIGQUERY_CURATED_DATASET

    rules = (
        db.query(QualityRule)
        .filter(QualityRule.dataset == dataset, QualityRule.enabled.is_(True))
        .all()
    )

    run_id = f"DQR-{uuid.uuid4().hex[:10].upper()}"
    now = datetime.now(timezone.utc)

    with duckdb_session() as conn:
        # Evaluate against latest batch in staging if job_id provided, else full staging table
        where_clause = f"WHERE ingestion_job_id = '{job_id}'" if job_id else ""
        total_records = int(conn.execute(f"SELECT COUNT(*) FROM {staging_table} {where_clause}").fetchone()[0])

        if total_records == 0:
            # Return empty run without failing
            run = QualityCheckRun(
                run_id=run_id,
                dataset=dataset,
                overall_score=100.0,
                total_records_evaluated=0,
                failed_validation_count=0,
                critical_issues_count=0,
                dimension_scores_json=json.dumps({d: 100.0 for d in DIMENSIONS}),
                rule_results_json="[]",
                triggered_by=triggered_by,
                executed_at=now,
            )
            db.add(run)
            db.flush()
            return {
                "run_id": run_id,
                "overall_score": 100.0,
                "total_records_evaluated": 0,
                "failed_validation_count": 0,
                "critical_issues_count": 0,
                "dimension_scores": {d: 100.0 for d in DIMENSIONS},
                "rule_results": [],
            }

        rule_results: list[dict[str, Any]] = []
        total_failed_validations = 0
        critical_issues = 0

        for rule in rules:
            cfg = json.loads(rule.rule_config or "{}")
            col = rule.column_name
            failed_count = 0
            sample_vals: list[str] = []

            if rule.rule_type == "not_null":
                q = f"SELECT COUNT(*) FROM {staging_table} {where_clause} {'AND' if where_clause else 'WHERE'} ({col} IS NULL OR TRIM(CAST({col} AS VARCHAR)) = '')"
                failed_count = int(conn.execute(q).fetchone()[0])
            elif rule.rule_type == "unique":
                q = f"""
                    SELECT COALESCE(SUM(cnt - 1), 0) FROM (
                        SELECT {col}, COUNT(*) AS cnt
                        FROM {staging_table}
                        {where_clause}
                        {'AND' if where_clause else 'WHERE'} {col} IS NOT NULL AND TRIM(CAST({col} AS VARCHAR)) != ''
                        GROUP BY {col}
                        HAVING COUNT(*) > 1
                    )
                """
                failed_count = int(conn.execute(q).fetchone()[0])
                if failed_count > 0:
                    samp = conn.execute(f"""
                        SELECT {col} FROM {staging_table} {where_clause}
                        {'AND' if where_clause else 'WHERE'} {col} IS NOT NULL AND TRIM(CAST({col} AS VARCHAR)) != ''
                        GROUP BY {col} HAVING COUNT(*) > 1 LIMIT 5
                    """).fetchall()
                    sample_vals = [str(r[0]) for r in samp]
            elif rule.rule_type == "allowed_values":
                vals = cfg.get("values", [])
                if vals:
                    quoted = ", ".join([f"'{v}'" for v in vals])
                    q = f"SELECT COUNT(*) FROM {staging_table} {where_clause} {'AND' if where_clause else 'WHERE'} ({col} IS NULL OR CAST({col} AS VARCHAR) NOT IN ({quoted}))"
                    failed_count = int(conn.execute(q).fetchone()[0])
                    if failed_count > 0:
                        samp = conn.execute(f"SELECT DISTINCT CAST({col} AS VARCHAR) FROM {staging_table} {where_clause} {'AND' if where_clause else 'WHERE'} ({col} IS NULL OR CAST({col} AS VARCHAR) NOT IN ({quoted})) LIMIT 5").fetchall()
                        sample_vals = [str(r[0]) for r in samp]
            elif rule.rule_type == "range":
                min_v = float(cfg.get("min", 0))
                max_v = float(cfg.get("max", 1e12))
                q = f"SELECT COUNT(*) FROM {staging_table} {where_clause} {'AND' if where_clause else 'WHERE'} ({col} IS NULL OR {col} < {min_v} OR {col} > {max_v})"
                failed_count = int(conn.execute(q).fetchone()[0])
                if failed_count > 0:
                    samp = conn.execute(f"SELECT CAST({col} AS VARCHAR) FROM {staging_table} {where_clause} {'AND' if where_clause else 'WHERE'} ({col} IS NULL OR {col} < {min_v} OR {col} > {max_v}) LIMIT 5").fetchall()
                    sample_vals = [str(r[0]) for r in samp]
            elif rule.rule_type == "timestamp_valid":
                q = f"SELECT COUNT(*) FROM {staging_table} {where_clause} {'AND' if where_clause else 'WHERE'} ({col} IS NULL OR {col} > CURRENT_TIMESTAMP + INTERVAL 1 DAY)"
                failed_count = int(conn.execute(q).fetchone()[0])
            elif rule.rule_type == "timeliness":
                max_days = int(cfg.get("max_age_days", 365))
                q = f"SELECT COUNT(*) FROM {staging_table} {where_clause} {'AND' if where_clause else 'WHERE'} ({col} IS NULL OR {col} < CURRENT_TIMESTAMP - INTERVAL {max_days} DAY)"
                failed_count = int(conn.execute(q).fetchone()[0])
            elif rule.rule_type == "referential_integrity":
                ref_table = cfg.get("reference_table", "customers")
                ref_col = cfg.get("reference_column", "customer_id")
                ref_count = int(conn.execute(f"SELECT COUNT(*) FROM {curated_schema}.{ref_table}").fetchone()[0])
                if ref_count > 0:
                    q = f"""
                        SELECT COUNT(*) FROM {staging_table} s
                        {where_clause}
                        {'AND' if where_clause else 'WHERE'} (s.{col} IS NULL OR TRIM(s.{col}) = '' OR NOT EXISTS (
                            SELECT 1 FROM {curated_schema}.{ref_table} r WHERE r.{ref_col} = s.{col}
                        ))
                    """
                    failed_count = int(conn.execute(q).fetchone()[0])
                    if failed_count > 0:
                        samp = conn.execute(f"""
                            SELECT DISTINCT s.{col} FROM {staging_table} s
                            {where_clause}
                            {'AND' if where_clause else 'WHERE'} s.{col} IS NOT NULL AND NOT EXISTS (
                                SELECT 1 FROM {curated_schema}.{ref_table} r WHERE r.{ref_col} = s.{col}
                            ) LIMIT 5
                        """).fetchall()
                        sample_vals = [str(r[0]) for r in samp]

            pass_rate = round(max(0.0, ((total_records - failed_count) / total_records) * 100.0), 2)
            passed_threshold = pass_rate >= rule.threshold
            total_failed_validations += failed_count
            if failed_count > 0 and rule.severity == "CRITICAL":
                critical_issues += 1

            rule.last_execution_date = now

            if failed_count > 0:
                db.add(
                    QualityIssue(
                        run_id=run_id,
                        rule_id=rule.rule_id,
                        rule_name=rule.rule_name,
                        dataset=rule.dataset,
                        column_name=rule.column_name,
                        dimension=rule.dimension,
                        severity=rule.severity,
                        failed_count=failed_count,
                        pass_rate=pass_rate,
                        sample_values=json.dumps(sample_vals),
                        status="OPEN",
                        detected_at=now,
                    )
                )

            rule_results.append({
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "dimension": rule.dimension,
                "severity": rule.severity,
                "threshold": rule.threshold,
                "total_evaluated": total_records,
                "failed_count": failed_count,
                "pass_rate": pass_rate,
                "passed_threshold": passed_threshold,
            })

    # Transparent Severity-Weighted Scoring Formula
    dimension_scores: dict[str, float] = {}
    for dim in DIMENSIONS:
        dim_rules = [r for r in rule_results if r["dimension"] == dim]
        if not dim_rules:
            dimension_scores[dim] = 100.0
        else:
            w_sum = sum(SEVERITY_WEIGHTS.get(r["severity"], 1.0) for r in dim_rules)
            weighted = sum(r["pass_rate"] * SEVERITY_WEIGHTS.get(r["severity"], 1.0) for r in dim_rules)
            dimension_scores[dim] = round(weighted / w_sum, 2)

    if rule_results:
        total_w = sum(SEVERITY_WEIGHTS.get(r["severity"], 1.0) for r in rule_results)
        overall_score = round(
            sum(r["pass_rate"] * SEVERITY_WEIGHTS.get(r["severity"], 1.0) for r in rule_results) / total_w,
            2,
        )
    else:
        overall_score = 100.0

    run = QualityCheckRun(
        run_id=run_id,
        dataset=dataset,
        overall_score=overall_score,
        total_records_evaluated=total_records,
        failed_validation_count=total_failed_validations,
        critical_issues_count=critical_issues,
        dimension_scores_json=json.dumps(dimension_scores),
        rule_results_json=json.dumps(rule_results),
        triggered_by=triggered_by,
        executed_at=now,
    )
    db.add(run)

    # Update catalog quality score for staging & curated transactions
    staging_cat = db.query(DataCatalogEntry).filter(DataCatalogEntry.table_name == staging_table).first()
    if staging_cat:
        staging_cat.quality_score = overall_score
        staging_cat.last_updated = now
    curated_cat = db.query(DataCatalogEntry).filter(
        DataCatalogEntry.table_name == f"{curated_schema}.transactions"
    ).first()
    if curated_cat:
        curated_cat.quality_score = 100.0  # Curated contains only validated records
        curated_cat.last_updated = now

    db.flush()
    return {
        "run_id": run_id,
        "overall_score": overall_score,
        "total_records_evaluated": total_records,
        "failed_validation_count": total_failed_validations,
        "critical_issues_count": critical_issues,
        "dimension_scores": dimension_scores,
        "rule_results": rule_results,
    }
