"""FastAPI application entrypoint for FinGuard AI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import (
    auth,
    credit_risk,
    dashboard,
    data_quality,
    fraud,
    governance,
    ingestion,
    reports,
    transactions,
)
from backend.app.core.bootstrap import init_all_databases
from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal
from backend.app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        init_all_databases(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="FinGuard AI — Enterprise Credit & Fraud Risk Data Governance Platform",
    description=(
        "Enterprise-grade synthetic financial data engineering, 7-dimension data quality, "
        "governance catalog & lineage, explainable fraud detection, and credit risk analytics API. "
        "All financial data is 100% synthetic."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(ingestion.router)
app.include_router(data_quality.router)
app.include_router(governance.router)
app.include_router(fraud.router)
app.include_router(credit_risk.router)
app.include_router(reports.router)
