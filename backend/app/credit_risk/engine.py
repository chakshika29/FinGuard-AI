"""Credit Risk Analytics Engine (Educational Demonstration Model).

DISCLAIMER:
This credit risk scoring module is an educational demonstration based on synthetic
account balances and repayment statuses. It is NOT a validated credit decisioning
system and must NOT be used for actual lending decisions.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.config import get_settings
from backend.app.core.database import duckdb_session
from backend.app.core.security import mask_card_token


def get_credit_risk_summary() -> dict[str, Any]:
    """Compute portfolio-level credit risk exposure, utilization, delinquency, and segment breakdowns."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET

    with duckdb_session() as conn:
        totals = conn.execute(f"""
            SELECT
                COUNT(*) AS total_accounts,
                COALESCE(SUM(credit_limit), 0) AS total_credit_limit,
                COALESCE(SUM(outstanding_balance), 0) AS total_outstanding_balance,
                COALESCE(AVG(credit_utilization_ratio), 0) AS avg_utilization,
                SUM(CASE WHEN credit_utilization_ratio >= 0.75 THEN 1 ELSE 0 END) AS high_utilization_accounts,
                SUM(CASE WHEN repayment_status != 'CURRENT' THEN 1 ELSE 0 END) AS overdue_accounts,
                SUM(CASE WHEN credit_risk_tier IN ('HIGH', 'CRITICAL') THEN 1 ELSE 0 END) AS high_risk_accounts,
                COALESCE(AVG(credit_risk_score), 0) AS avg_credit_risk_score
            FROM {curated}.accounts
        """).fetchone()

        total_accounts = int(totals[0] or 0)
        if total_accounts == 0:
            return {
                "disclaimer": "Educational demonstration model only — not a validated credit decision system.",
                "total_accounts": 0,
                "total_credit_limit": 0.0,
                "total_outstanding_balance": 0.0,
                "avg_utilization_pct": 0.0,
                "high_utilization_accounts": 0,
                "overdue_accounts": 0,
                "overdue_rate_pct": 0.0,
                "high_risk_accounts": 0,
                "avg_credit_risk_score": 0.0,
                "repayment_distribution": [],
                "exposure_by_segment": [],
                "exposure_by_risk_category": [],
                "utilization_buckets": [],
            }

        repay_rows = conn.execute(f"""
            SELECT
                repayment_status,
                COUNT(*) AS account_count,
                ROUND(SUM(outstanding_balance), 2) AS total_exposure,
                ROUND(AVG(credit_utilization_ratio) * 100, 2) AS avg_utilization_pct
            FROM {curated}.accounts
            GROUP BY repayment_status
            ORDER BY account_count DESC
        """).fetchall()

        seg_rows = conn.execute(f"""
            SELECT
                COALESCE(c.customer_segment, 'UNKNOWN') AS segment,
                COUNT(*) AS account_count,
                ROUND(SUM(a.credit_limit), 2) AS total_limit,
                ROUND(SUM(a.outstanding_balance), 2) AS total_exposure,
                ROUND(AVG(a.credit_utilization_ratio) * 100, 2) AS avg_utilization_pct,
                ROUND(AVG(a.credit_risk_score), 2) AS avg_risk_score
            FROM {curated}.accounts a
            LEFT JOIN {curated}.customers c ON a.customer_id = c.customer_id
            GROUP BY segment
            ORDER BY total_exposure DESC
        """).fetchall()

        risk_rows = conn.execute(f"""
            SELECT
                COALESCE(c.customer_risk_category, 'UNKNOWN') AS risk_category,
                COUNT(*) AS account_count,
                ROUND(SUM(a.outstanding_balance), 2) AS total_exposure,
                ROUND(AVG(a.credit_utilization_ratio) * 100, 2) AS avg_utilization_pct
            FROM {curated}.accounts a
            LEFT JOIN {curated}.customers c ON a.customer_id = c.customer_id
            GROUP BY risk_category
            ORDER BY total_exposure DESC
        """).fetchall()

        util_buckets = conn.execute(f"""
            SELECT
                CASE
                    WHEN credit_utilization_ratio < 0.25 THEN '0-25%'
                    WHEN credit_utilization_ratio < 0.50 THEN '25-50%'
                    WHEN credit_utilization_ratio < 0.75 THEN '50-75%'
                    WHEN credit_utilization_ratio < 0.90 THEN '75-90%'
                    ELSE '90%+'
                END AS bucket,
                COUNT(*) AS account_count,
                ROUND(SUM(outstanding_balance), 2) AS total_exposure
            FROM {curated}.accounts
            GROUP BY bucket
            ORDER BY bucket
        """).fetchall()

    overdue = int(totals[5] or 0)
    return {
        "disclaimer": "Educational demonstration model only — not a validated credit decision system.",
        "total_accounts": total_accounts,
        "total_credit_limit": round(float(totals[1] or 0.0), 2),
        "total_outstanding_balance": round(float(totals[2] or 0.0), 2),
        "avg_utilization_pct": round(float(totals[3] or 0.0) * 100.0, 2),
        "high_utilization_accounts": int(totals[4] or 0),
        "overdue_accounts": overdue,
        "overdue_rate_pct": round((overdue / total_accounts) * 100.0, 2),
        "high_risk_accounts": int(totals[6] or 0),
        "avg_credit_risk_score": round(float(totals[7] or 0.0), 2),
        "repayment_distribution": [
            {
                "repayment_status": r[0],
                "account_count": int(r[1]),
                "total_exposure": float(r[2] or 0),
                "avg_utilization_pct": float(r[3] or 0),
            }
            for r in repay_rows
        ],
        "exposure_by_segment": [
            {
                "segment": r[0],
                "account_count": int(r[1]),
                "total_limit": float(r[2] or 0),
                "total_exposure": float(r[3] or 0),
                "avg_utilization_pct": float(r[4] or 0),
                "avg_risk_score": float(r[5] or 0),
            }
            for r in seg_rows
        ],
        "exposure_by_risk_category": [
            {
                "risk_category": r[0],
                "account_count": int(r[1]),
                "total_exposure": float(r[2] or 0),
                "avg_utilization_pct": float(r[3] or 0),
            }
            for r in risk_rows
        ],
        "utilization_buckets": [
            {"bucket": r[0], "account_count": int(r[1]), "total_exposure": float(r[2] or 0)}
            for r in util_buckets
        ],
    }


def list_credit_accounts(
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    repayment_status: str | None = None,
    risk_tier: str | None = None,
    min_utilization: float | None = None,
) -> dict[str, Any]:
    """Paginated customer/account credit risk profiles with masked card tokens."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET

    filters = ["1=1"]
    params: list[Any] = []
    if search:
        filters.append("(a.account_id ILIKE ? OR a.customer_id ILIKE ? OR c.customer_segment ILIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if repayment_status:
        filters.append("a.repayment_status = ?")
        params.append(repayment_status.upper())
    if risk_tier:
        filters.append("a.credit_risk_tier = ?")
        params.append(risk_tier.upper())
    if min_utilization is not None:
        filters.append("a.credit_utilization_ratio >= ?")
        params.append(min_utilization)

    where_sql = " AND ".join(filters)
    offset = (page - 1) * page_size

    with duckdb_session() as conn:
        total = int(
            conn.execute(
                f"""
                SELECT COUNT(*)
                FROM {curated}.accounts a
                LEFT JOIN {curated}.customers c ON a.customer_id = c.customer_id
                WHERE {where_sql}
                """,
                params,
            ).fetchone()[0]
        )
        rows = conn.execute(
            f"""
            SELECT
                a.account_id,
                a.customer_id,
                a.card_token,
                a.credit_limit,
                a.outstanding_balance,
                a.credit_utilization_ratio,
                a.repayment_status,
                a.delinquency_days,
                a.account_status,
                a.credit_risk_score,
                a.credit_risk_tier,
                COALESCE(c.customer_segment, 'UNKNOWN') AS customer_segment,
                COALESCE(c.customer_risk_category, 'MEDIUM') AS customer_risk_category,
                COALESCE(c.home_country, 'US') AS home_country
            FROM {curated}.accounts a
            LEFT JOIN {curated}.customers c ON a.customer_id = c.customer_id
            WHERE {where_sql}
            ORDER BY a.credit_risk_score DESC, a.credit_utilization_ratio DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

    items = [
        {
            "account_id": r[0],
            "customer_id": r[1],
            "card_token_masked": mask_card_token(r[2]),
            "credit_limit": float(r[3]),
            "outstanding_balance": float(r[4]),
            "credit_utilization_pct": round(float(r[5]) * 100.0, 2),
            "repayment_status": r[6],
            "delinquency_days": int(r[7]),
            "account_status": r[8],
            "credit_risk_score": float(r[9]),
            "credit_risk_tier": r[10],
            "customer_segment": r[11],
            "customer_risk_category": r[12],
            "home_country": r[13],
        }
        for r in rows
    ]

    return {
        "disclaimer": "Educational demonstration model only — not a validated credit decision system.",
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
