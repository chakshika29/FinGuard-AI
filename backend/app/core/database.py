"""Database connection managers for operational metadata (SQLAlchemy) and analytical warehouse (DuckDB)."""

import threading
from contextlib import contextmanager
from typing import Generator

import duckdb
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.metadata_db_url,
    connect_args={"check_same_thread": False} if settings.metadata_db_url.startswith("sqlite") else {},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


class Base(DeclarativeBase):
    """Declarative base for SQLAlchemy metadata models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_duckdb_lock = threading.RLock()


def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection to the local analytical warehouse file."""
    db_path = settings.duckdb_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


@contextmanager
def duckdb_session() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Thread-safe context manager for DuckDB queries and transactions."""
    with _duckdb_lock:
        conn = get_duckdb_connection()
        try:
            yield conn
        finally:
            conn.close()


def init_duckdb_warehouse() -> None:
    """Create the 5-layer enterprise data warehouse schemas and tables in DuckDB."""
    raw_schema = settings.BIGQUERY_RAW_DATASET
    staging_schema = settings.BIGQUERY_STAGING_DATASET
    curated_schema = settings.BIGQUERY_CURATED_DATASET
    gov_schema = settings.BIGQUERY_GOVERNANCE_DATASET
    analytics_schema = settings.BIGQUERY_ANALYTICS_DATASET

    ddl = f"""
    CREATE SCHEMA IF NOT EXISTS {raw_schema};
    CREATE SCHEMA IF NOT EXISTS {staging_schema};
    CREATE SCHEMA IF NOT EXISTS {curated_schema};
    CREATE SCHEMA IF NOT EXISTS {gov_schema};
    CREATE SCHEMA IF NOT EXISTS {analytics_schema};

    CREATE TABLE IF NOT EXISTS {raw_schema}.transactions_raw (
        transaction_id VARCHAR,
        customer_id VARCHAR,
        account_id VARCHAR,
        card_token VARCHAR,
        transaction_timestamp VARCHAR,
        transaction_amount VARCHAR,
        currency VARCHAR,
        merchant_id VARCHAR,
        merchant_category VARCHAR,
        transaction_type VARCHAR,
        payment_method VARCHAR,
        transaction_country VARCHAR,
        transaction_city VARCHAR,
        device_id VARCHAR,
        transaction_status VARCHAR,
        credit_limit VARCHAR,
        outstanding_balance VARCHAR,
        repayment_status VARCHAR,
        customer_risk_category VARCHAR,
        fraud_label VARCHAR,
        ingestion_timestamp VARCHAR,
        source_system VARCHAR,
        ingestion_job_id VARCHAR,
        file_checksum VARCHAR,
        source_file VARCHAR,
        source_row_number INTEGER,
        loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS {staging_schema}.transactions_staging (
        transaction_id VARCHAR,
        customer_id VARCHAR,
        account_id VARCHAR,
        card_token VARCHAR,
        transaction_timestamp TIMESTAMP,
        transaction_amount DOUBLE,
        currency VARCHAR,
        merchant_id VARCHAR,
        merchant_category VARCHAR,
        transaction_type VARCHAR,
        payment_method VARCHAR,
        transaction_country VARCHAR,
        transaction_city VARCHAR,
        device_id VARCHAR,
        transaction_status VARCHAR,
        credit_limit DOUBLE,
        outstanding_balance DOUBLE,
        repayment_status VARCHAR,
        customer_risk_category VARCHAR,
        fraud_label INTEGER,
        ingestion_timestamp TIMESTAMP,
        source_system VARCHAR,
        ingestion_job_id VARCHAR,
        is_valid BOOLEAN,
        validation_errors VARCHAR,
        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS {curated_schema}.customers (
        customer_id VARCHAR PRIMARY KEY,
        full_name_synthetic VARCHAR,
        customer_segment VARCHAR,
        customer_risk_category VARCHAR,
        home_country VARCHAR,
        home_city VARCHAR,
        income_band VARCHAR,
        account_open_date DATE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS {curated_schema}.accounts (
        account_id VARCHAR PRIMARY KEY,
        customer_id VARCHAR,
        card_token VARCHAR,
        credit_limit DOUBLE,
        outstanding_balance DOUBLE,
        credit_utilization_ratio DOUBLE,
        repayment_status VARCHAR,
        delinquency_days INTEGER,
        account_status VARCHAR,
        credit_risk_score DOUBLE,
        credit_risk_tier VARCHAR,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS {curated_schema}.merchants (
        merchant_id VARCHAR PRIMARY KEY,
        merchant_name VARCHAR,
        merchant_category VARCHAR,
        merchant_country VARCHAR,
        merchant_risk_tier VARCHAR,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS {curated_schema}.transactions (
        transaction_id VARCHAR PRIMARY KEY,
        customer_id VARCHAR,
        account_id VARCHAR,
        card_token VARCHAR,
        transaction_timestamp TIMESTAMP,
        transaction_date DATE,
        transaction_amount DOUBLE,
        currency VARCHAR,
        merchant_id VARCHAR,
        merchant_category VARCHAR,
        transaction_type VARCHAR,
        payment_method VARCHAR,
        transaction_country VARCHAR,
        transaction_city VARCHAR,
        device_id VARCHAR,
        transaction_status VARCHAR,
        credit_limit DOUBLE,
        outstanding_balance DOUBLE,
        repayment_status VARCHAR,
        customer_risk_category VARCHAR,
        fraud_label INTEGER,
        ingestion_timestamp TIMESTAMP,
        source_system VARCHAR,
        ingestion_job_id VARCHAR,
        fraud_risk_score DOUBLE DEFAULT 0.0,
        fraud_risk_level VARCHAR DEFAULT 'Low Risk',
        risk_explanations VARCHAR DEFAULT '[]',
        ml_anomaly_score DOUBLE DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS {gov_schema}.quarantined_records (
        quarantine_id VARCHAR PRIMARY KEY,
        ingestion_job_id VARCHAR,
        transaction_id VARCHAR,
        source_file VARCHAR,
        source_row_number INTEGER,
        raw_payload VARCHAR,
        failure_reasons VARCHAR,
        failed_rules VARCHAR,
        severity VARCHAR,
        remediation_status VARCHAR DEFAULT 'OPEN',
        remediation_notes VARCHAR DEFAULT '',
        quarantined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS {analytics_schema}.daily_transaction_metrics (
        transaction_date DATE PRIMARY KEY,
        total_transactions BIGINT,
        total_value DOUBLE,
        avg_amount DOUBLE,
        suspicious_count BIGINT,
        high_risk_count BIGINT,
        failed_tx_count BIGINT
    );

    CREATE TABLE IF NOT EXISTS {analytics_schema}.merchant_risk_summary (
        merchant_category VARCHAR PRIMARY KEY,
        total_transactions BIGINT,
        total_value DOUBLE,
        avg_fraud_score DOUBLE,
        suspicious_count BIGINT,
        suspicious_rate DOUBLE
    );
    """
    with duckdb_session() as conn:
        conn.execute(ddl)
