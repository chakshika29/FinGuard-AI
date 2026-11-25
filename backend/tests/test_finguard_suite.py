"""Comprehensive automated test suite for FinGuard AI."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.main import app
from backend.app.pipelines.etl import run_etl_pipeline
from backend.app.pipelines.generator import generate_synthetic_dataset
from backend.app.services.gcp_service import GCPIntegrationService


@pytest.fixture(scope="module")
def isolated_env():
    """Run integration tests against an isolated temporary warehouse & metadata DB."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="finguard_test_"))
    settings = get_settings()
    orig_duckdb = settings.LOCAL_DUCKDB_PATH
    orig_meta = settings.LOCAL_METADATA_DB_URL
    orig_raw = settings.DATA_RAW_DIR
    orig_proc = settings.DATA_PROCESSED_DIR

    settings.LOCAL_DUCKDB_PATH = str(tmp_dir / "test_warehouse.duckdb")
    settings.LOCAL_METADATA_DB_URL = f"sqlite:///{(tmp_dir / 'test_meta.db').as_posix()}"
    settings.DATA_RAW_DIR = str(tmp_dir / "raw")
    settings.DATA_PROCESSED_DIR = str(tmp_dir / "processed")

    # Rebind SQLAlchemy engine & SessionLocal for test isolation
    import backend.app.core.database as db_mod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_mod.engine = create_engine(settings.metadata_db_url, connect_args={"check_same_thread": False}, future=True)
    db_mod.SessionLocal = sessionmaker(bind=db_mod.engine, autocommit=False, autoflush=False)

    # Also update imported references in modules
    import backend.app.core.bootstrap as boot_mod
    import backend.app.main as main_mod
    import backend.app.pipelines.etl as etl_mod

    boot_mod.engine = db_mod.engine
    main_mod.SessionLocal = db_mod.SessionLocal
    etl_mod.SessionLocal = db_mod.SessionLocal

    with TestClient(app) as client:
        yield client, tmp_dir

    settings.LOCAL_DUCKDB_PATH = orig_duckdb
    settings.LOCAL_METADATA_DB_URL = orig_meta
    settings.DATA_RAW_DIR = orig_raw
    settings.DATA_PROCESSED_DIR = orig_proc
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _get_token(client: TestClient, username: str, password: str) -> str:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def test_health_endpoint(isolated_env):
    client, _ = isolated_env
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert res.json()["backend_mode"] == "local"


def test_authentication_and_rbac(isolated_env):
    client, _ = isolated_env
    settings = get_settings()

    # Invalid login
    bad = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad.status_code == 401

    # Valid logins for all 3 roles
    admin_tok = _get_token(client, "admin", settings.DEMO_ADMIN_PASSWORD)
    steward_tok = _get_token(client, "steward", settings.DEMO_STEWARD_PASSWORD)
    analyst_tok = _get_token(client, "analyst", settings.DEMO_ANALYST_PASSWORD)

    # Analyst cannot create quality rules or list users
    r_rule = client.post(
        "/api/data-quality/rules",
        headers={"Authorization": f"Bearer {analyst_tok}"},
        json={
            "rule_name": "Blocked Rule",
            "description": "Should fail for Risk Analyst",
            "column_name": "currency",
            "dimension": "Validity",
            "severity": "LOW",
            "rule_type": "not_null",
        },
    )
    assert r_rule.status_code == 403

    # Steward cannot update governance policies (Admin only)
    r_pol = client.patch(
        "/api/governance/policies/POL-001",
        headers={"Authorization": f"Bearer {steward_tok}"},
        json={"enabled": False},
    )
    assert r_pol.status_code == 403

    # Admin can list users
    r_users = client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_tok}"})
    assert r_users.status_code == 200
    assert len(r_users.json()) >= 3


def test_reproducible_synthetic_generator(tmp_path):
    r1 = generate_synthetic_dataset(num_records=500, seed=123, output_dir=tmp_path / "run1", prefix="t1")
    r2 = generate_synthetic_dataset(num_records=500, seed=123, output_dir=tmp_path / "run2", prefix="t2")

    assert r1["manifest"]["num_records"] == 500
    assert r1["manifest"]["synthetic_fraud_count"] == r2["manifest"]["synthetic_fraud_count"]
    assert r1["manifest"]["injected_quality_issues_summary"] == r2["manifest"]["injected_quality_issues_summary"]
    assert r1["manifest"]["total_injected_issues"] >= 8


def test_end_to_end_10k_etl_quality_fraud_credit_governance_export(isolated_env, tmp_path):
    client, _ = isolated_env
    settings = get_settings()
    admin_tok = _get_token(client, "admin", settings.DEMO_ADMIN_PASSWORD)
    steward_tok = _get_token(client, "steward", settings.DEMO_STEWARD_PASSWORD)
    analyst_tok = _get_token(client, "analyst", settings.DEMO_ANALYST_PASSWORD)

    # 1. Generate 10,000 records dataset & run ETL synchronously via pipeline
    gen = generate_synthetic_dataset(num_records=10000, seed=77, output_dir=tmp_path, quality_issue_rate=0.03)

    import backend.app.core.database as db_mod
    db = db_mod.SessionLocal()
    try:
        etl_res = run_etl_pipeline(
            db=db,
            job_id="JOB-TEST-10K",
            file_path=gen["transactions_file"],
            triggered_by="admin",
            customers_file=gen["customers_file"],
            accounts_file=gen["accounts_file"],
            merchants_file=gen["merchants_file"],
        )
        assert etl_res["records_received"] == 10000
        assert etl_res["valid_records"] > 9500
        assert etl_res["invalid_records"] > 100
        assert etl_res["quarantined_records"] == etl_res["invalid_records"]
        assert etl_res["duplicate_records"] >= 1

        # 2. Test Idempotent Re-Ingestion of the EXACT same file
        idem_res = run_etl_pipeline(
            db=db,
            job_id="JOB-TEST-10K-RETRY",
            file_path=gen["transactions_file"],
            triggered_by="admin",
        )
        assert idem_res["idempotent_skip"] is True
        assert idem_res["status"] == "COMPLETED_IDEMPOTENT"
    finally:
        db.close()

    # 3. Verify Dashboard & Transactions API
    dash = client.get("/api/dashboard/summary", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert dash.status_code == 200
    assert dash.json()["kpis"]["total_transactions"] == etl_res["valid_records"]

    tx_list = client.get("/api/transactions?page=1&page_size=10", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert tx_list.status_code == 200
    first_tx = tx_list.json()["items"][0]
    assert first_tx["card_token_masked"].startswith("****")

    tx_detail = client.get(f"/api/transactions/{first_tx['transaction_id']}", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert tx_detail.status_code == 200

    # 4. Verify Data Quality Summary, Rule Creation, Toggle, Quarantine Remediation
    dq_sum = client.get("/api/data-quality/summary", headers={"Authorization": f"Bearer {steward_tok}"})
    assert dq_sum.status_code == 200
    assert len(dq_sum.json()["dimension_scores"]) == 7

    qr_res = client.get("/api/data-quality/quarantine?page=1&page_size=5", headers={"Authorization": f"Bearer {steward_tok}"})
    assert qr_res.status_code == 200
    assert qr_res.json()["total"] == etl_res["quarantined_records"]
    qid = qr_res.json()["items"][0]["quarantine_id"]

    rem_res = client.patch(
        f"/api/data-quality/quarantine/{qid}",
        headers={"Authorization": f"Bearer {steward_tok}"},
        json={"remediation_status": "RESOLVED", "remediation_notes": "Verified synthetic test issue"},
    )
    assert rem_res.status_code == 200
    assert rem_res.json()["remediation_status"] == "RESOLVED"

    # 5. Verify Fraud Summary, ML IsolationForest Evaluation & Alert Review
    ml_res = client.post("/api/fraud/train-ml", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert ml_res.status_code == 200
    assert 0.0 <= ml_res.json()["precision"] <= 1.0
    assert ml_res.json()["test_size"] > 1000

    alerts = client.get("/api/fraud/alerts?page=1&page_size=5", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert alerts.status_code == 200
    assert alerts.json()["total"] > 0
    aid = alerts.json()["items"][0]["alert_id"]
    rev = client.patch(
        f"/api/fraud/alerts/{aid}",
        headers={"Authorization": f"Bearer {analyst_tok}"},
        json={"investigation_status": "INVESTIGATING", "analyst_notes": "Checking velocity"},
    )
    assert rev.status_code == 200

    # 6. Verify Credit Risk Summary & Accounts
    cr_sum = client.get("/api/credit-risk/summary", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert cr_sum.status_code == 200
    assert cr_sum.json()["total_accounts"] > 0
    cr_accts = client.get("/api/credit-risk/accounts?page=1&page_size=5", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert cr_accts.status_code == 200

    # 7. Verify Governance Catalog, Lineage, Policies, Audit Logs
    cat = client.get("/api/governance/catalog", headers={"Authorization": f"Bearer {steward_tok}"})
    assert cat.status_code == 200
    assert len(cat.json()) >= 8

    lin = client.get("/api/governance/lineage", headers={"Authorization": f"Bearer {steward_tok}"})
    assert lin.status_code == 200
    assert len(lin.json()["recent_events"]) >= 4

    aud = client.get("/api/governance/audit-logs", headers={"Authorization": f"Bearer {admin_tok}"})
    assert aud.status_code == 200
    assert aud.json()["total"] >= 5

    # 8. Verify CSV Export & BigQuery Sandbox CSV Export
    csv_res = client.get("/api/reports/export?report_type=transactions&limit=50", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert csv_res.status_code == 200
    assert "transaction_id" in csv_res.text

    sb_res = client.get("/api/reports/export?report_type=bigquery_sandbox", headers={"Authorization": f"Bearer {analyst_tok}"})
    assert sb_res.status_code == 200
    assert sb_res.json()["status"] == "exported"
    assert len(sb_res.json()["files"]) == 5


def test_schema_validation_rejects_missing_columns(isolated_env, tmp_path):
    _, _ = isolated_env
    bad_csv = tmp_path / "bad_schema.csv"
    bad_csv.write_text("col_a,col_b\n1,2\n", encoding="utf-8")

    import backend.app.core.database as db_mod
    db = db_mod.SessionLocal()
    try:
        with pytest.raises(ValueError, match="Schema mismatch"):
            run_etl_pipeline(db=db, job_id="JOB-BAD-SCHEMA", file_path=bad_csv, triggered_by="admin")
    finally:
        db.close()


def test_json_ingestion_format(isolated_env, tmp_path):
    _, _ = isolated_env
    gen = generate_synthetic_dataset(num_records=200, seed=99, output_dir=tmp_path, file_format="json", prefix="json_test")
    import backend.app.core.database as db_mod
    db = db_mod.SessionLocal()
    try:
        res = run_etl_pipeline(
            db=db,
            job_id="JOB-JSON-200",
            file_path=gen["transactions_file"],
            triggered_by="steward",
            customers_file=gen["customers_file"],
            accounts_file=gen["accounts_file"],
            merchants_file=gen["merchants_file"],
        )
        assert res["records_received"] == 200
        assert res["valid_records"] > 180
    finally:
        db.close()


def test_gcp_bigquery_and_gcs_integration_with_mocks(tmp_path):
    """Verify genuine GCP SDK calls (datasets, partitioned tables, dry-run cost, GCS upload) via mocks."""
    mock_bq_client = MagicMock()
    mock_gcs_client = MagicMock()

    mock_query_job = MagicMock()
    mock_query_job.total_bytes_processed = 104857600  # 100 MiB
    mock_bq_client.query.return_value = mock_query_job
    mock_bq_client.list_datasets.return_value = []

    sample_file = tmp_path / "sample.csv"
    sample_file.write_text("transaction_id,amount\nTX1,10.0\n", encoding="utf-8")

    with patch("backend.app.services.gcp_service.bigquery.Client", return_value=mock_bq_client), \
         patch("backend.app.services.gcp_service.storage.Client", return_value=mock_gcs_client):
        svc = GCPIntegrationService(project_id="finguard-demo-proj", location="US", bucket_name="finguard-raw-bucket")

        conn_status = svc.check_connection()
        assert conn_status["verified"] is True
        assert conn_status["mode"] == "bigquery"

        created_ds = svc.ensure_datasets_exist()
        assert len(created_ds) == 5
        assert mock_bq_client.create_dataset.call_count == 5

        table_id = svc.ensure_partitioned_curated_table()
        assert table_id == "finguard-demo-proj.finguard_curated.transactions"
        mock_bq_client.create_table.assert_called_once()

        cost = svc.estimate_query_cost("SELECT * FROM finguard_curated.transactions")
        assert cost["dry_run"] is True
        assert cost["total_mb_processed"] == 100.0
        assert cost["within_free_tier_1tb"] is True

        gs_uri = svc.upload_file_to_gcs(sample_file, "raw/sample.csv")
        assert gs_uri == "gs://finguard-raw-bucket/raw/sample.csv"
        mock_gcs_client.bucket.assert_called_with("finguard-raw-bucket")
