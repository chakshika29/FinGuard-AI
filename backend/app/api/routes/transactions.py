"""Transaction explorer routes with search, filtering, sorting, pagination, and masking."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.core.config import get_settings
from backend.app.core.database import duckdb_session
from backend.app.core.security import get_current_user, mask_card_token
from backend.app.models.metadata import User

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("")
def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=5, le=200),
    search: str | None = None,
    risk_level: str | None = None,
    status: str | None = None,
    country: str | None = None,
    merchant_category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = Query(default="transaction_timestamp", pattern="^(transaction_timestamp|transaction_amount|fraud_risk_score)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
):
    """Search, filter, and paginate curated financial transactions."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET

    filters = ["1=1"]
    params: list[Any] = []

    if search:
        filters.append("(transaction_id ILIKE ? OR customer_id ILIKE ? OR merchant_id ILIKE ? OR transaction_city ILIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like, like])
    if risk_level:
        filters.append("fraud_risk_level = ?")
        params.append(risk_level)
    if status:
        filters.append("transaction_status = ?")
        params.append(status.upper())
    if country:
        filters.append("transaction_country = ?")
        params.append(country.upper())
    if merchant_category:
        filters.append("merchant_category = ?")
        params.append(merchant_category.upper())
    if date_from:
        filters.append("transaction_date >= CAST(? AS DATE)")
        params.append(date_from)
    if date_to:
        filters.append("transaction_date <= CAST(? AS DATE)")
        params.append(date_to)

    where_sql = " AND ".join(filters)
    order_sql = f"{sort_by} {'DESC' if sort_dir == 'desc' else 'ASC'}"
    offset = (page - 1) * page_size

    with duckdb_session() as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM {curated}.transactions WHERE {where_sql}", params).fetchone()[0])
        rows = conn.execute(
            f"""
            SELECT
                transaction_id, customer_id, account_id, card_token,
                CAST(transaction_timestamp AS VARCHAR), transaction_amount, currency,
                merchant_id, merchant_category, transaction_type, payment_method,
                transaction_country, transaction_city, device_id, transaction_status,
                fraud_risk_score, fraud_risk_level, risk_explanations, customer_risk_category
            FROM {curated}.transactions
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

    items = [
        {
            "transaction_id": r[0],
            "customer_id": r[1],
            "account_id": r[2],
            "card_token_masked": mask_card_token(r[3]),
            "transaction_timestamp": r[4],
            "transaction_amount": float(r[5]),
            "currency": r[6],
            "merchant_id": r[7],
            "merchant_category": r[8],
            "transaction_type": r[9],
            "payment_method": r[10],
            "transaction_country": r[11],
            "transaction_city": r[12],
            "device_id": r[13],
            "transaction_status": r[14],
            "fraud_risk_score": float(r[15] or 0.0),
            "fraud_risk_level": r[16],
            "risk_explanations": json.loads(r[17] or "[]"),
            "customer_risk_category": r[18],
        }
        for r in rows
    ]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/{transaction_id}")
def get_transaction_detail(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieve complete curated transaction detail with masked card token and customer/merchant context."""
    settings = get_settings()
    curated = settings.BIGQUERY_CURATED_DATASET

    with duckdb_session() as conn:
        row = conn.execute(
            f"""
            SELECT
                t.transaction_id, t.customer_id, t.account_id, t.card_token,
                CAST(t.transaction_timestamp AS VARCHAR), t.transaction_amount, t.currency,
                t.merchant_id, t.merchant_category, t.transaction_type, t.payment_method,
                t.transaction_country, t.transaction_city, t.device_id, t.transaction_status,
                t.credit_limit, t.outstanding_balance, t.repayment_status, t.customer_risk_category,
                t.fraud_label, CAST(t.ingestion_timestamp AS VARCHAR), t.source_system,
                t.ingestion_job_id, t.fraud_risk_score, t.fraud_risk_level, t.risk_explanations,
                t.ml_anomaly_score, m.merchant_name, m.merchant_risk_tier, c.home_country, c.customer_segment
            FROM {curated}.transactions t
            LEFT JOIN {curated}.merchants m ON t.merchant_id = m.merchant_id
            LEFT JOIN {curated}.customers c ON t.customer_id = c.customer_id
            WHERE t.transaction_id = ?
            """,
            [transaction_id],
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found.")

    return {
        "transaction_id": row[0],
        "customer_id": row[1],
        "account_id": row[2],
        "card_token_masked": mask_card_token(row[3]),
        "transaction_timestamp": row[4],
        "transaction_amount": float(row[5]),
        "currency": row[6],
        "merchant_id": row[7],
        "merchant_category": row[8],
        "transaction_type": row[9],
        "payment_method": row[10],
        "transaction_country": row[11],
        "transaction_city": row[12],
        "device_id": row[13],
        "transaction_status": row[14],
        "credit_limit": float(row[15] or 0.0),
        "outstanding_balance": float(row[16] or 0.0),
        "repayment_status": row[17],
        "customer_risk_category": row[18],
        "synthetic_fraud_label": int(row[19] or 0),
        "ingestion_timestamp": row[20],
        "source_system": row[21],
        "ingestion_job_id": row[22],
        "fraud_risk_score": float(row[23] or 0.0),
        "fraud_risk_level": row[24],
        "risk_explanations": json.loads(row[25] or "[]"),
        "ml_anomaly_score": float(row[26] or 0.0),
        "merchant_name": row[27],
        "merchant_risk_tier": row[28],
        "customer_home_country": row[29],
        "customer_segment": row[30],
    }
