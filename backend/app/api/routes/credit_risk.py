"""Credit Risk Analytics routes."""

from fastapi import APIRouter, Depends, Query

from backend.app.core.security import get_current_user
from backend.app.credit_risk.engine import get_credit_risk_summary, list_credit_accounts
from backend.app.models.metadata import User

router = APIRouter(prefix="/api/credit-risk", tags=["Credit Risk Analytics"])


@router.get("/summary")
def credit_risk_summary(current_user: User = Depends(get_current_user)):
    """Portfolio-level credit utilization, exposure, repayment distribution, and delinquency KPIs."""
    return get_credit_risk_summary()


@router.get("/accounts")
def credit_risk_accounts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=5, le=200),
    search: str | None = None,
    repayment_status: str | None = None,
    risk_tier: str | None = None,
    min_utilization: float | None = Query(default=None, ge=0.0, le=2.0),
    current_user: User = Depends(get_current_user),
):
    """Paginated account-level credit risk profiles with masked card tokens."""
    return list_credit_accounts(
        page=page,
        page_size=page_size,
        search=search,
        repayment_status=repayment_status,
        risk_tier=risk_tier,
        min_utilization=min_utilization,
    )
