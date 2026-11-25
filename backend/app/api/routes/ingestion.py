"""Data ingestion routes: upload CSV/JSON, generate synthetic datasets, and monitor ETL jobs."""

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.core.security import ROLE_ADMIN, ROLE_STEWARD, get_current_user, require_roles
from backend.app.governance.audit_service import record_audit_log
from backend.app.models.metadata import IngestionJob, User
from backend.app.pipelines.etl import compute_sha256, execute_etl_job
from backend.app.pipelines.generator import generate_synthetic_dataset
from backend.app.schemas.api import GenerateDatasetRequest

router = APIRouter(prefix="/api/ingestion", tags=["Data Ingestion"])

ALLOWED_EXTENSIONS = {".csv", ".json"}


@router.post("/upload")
async def upload_transaction_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force_reprocess: bool = Form(default=False),
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_STEWARD)),
    db: Session = Depends(get_db),
):
    """Upload a CSV or JSON transaction batch and trigger asynchronous ETL processing."""
    settings = get_settings()
    filename = Path(file.filename or "upload.csv").name
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .csv and .json files are allowed.")

    job_id = f"JOB-{uuid.uuid4().hex[:10].upper()}"
    save_path = settings.raw_dir / f"{job_id}_{filename}"

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_size = 0
    with save_path.open("wb") as out_f:
        while chunk := await file.read(1024 * 1024):
            total_size += len(chunk)
            if total_size > max_bytes:
                save_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB upload limit.")
            out_f.write(chunk)

    checksum = compute_sha256(save_path)
    job = IngestionJob(
        id=job_id,
        source_file=filename,
        file_format=ext.lstrip("."),
        file_checksum=checksum,
        status="QUEUED",
        triggered_by=current_user.username,
        backend_target="bigquery" if settings.is_bigquery_mode else "local",
    )
    db.add(job)
    record_audit_log(
        db,
        actor=current_user.username,
        actor_role=current_user.role,
        action="FILE_UPLOAD_QUEUED",
        resource_type="ingestion_job",
        resource_id=job_id,
        updated_value=f"file={filename}, bytes={total_size}",
    )
    db.commit()

    background_tasks.add_task(
        execute_etl_job,
        job_id=job_id,
        file_path=save_path,
        triggered_by=current_user.username,
        force_reprocess=force_reprocess,
    )

    return {
        "job_id": job_id,
        "status": "QUEUED",
        "source_file": filename,
        "file_checksum": checksum,
        "message": "Ingestion job queued for asynchronous ETL execution.",
    }


@router.post("/generate")
def generate_and_ingest(
    payload: GenerateDatasetRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_roles(ROLE_ADMIN, ROLE_STEWARD)),
    db: Session = Depends(get_db),
):
    """Generate a reproducible synthetic financial dataset and optionally queue ETL ingestion."""
    settings = get_settings()
    gen_res = generate_synthetic_dataset(
        num_records=payload.num_records,
        seed=payload.seed,
        output_dir=settings.raw_dir,
        inject_quality_issues=payload.inject_quality_issues,
        quality_issue_rate=payload.quality_issue_rate,
        fraud_rate=payload.fraud_rate,
        file_format=payload.file_format,
    )

    tx_path = Path(gen_res["transactions_file"])
    job_id = f"JOB-{uuid.uuid4().hex[:10].upper()}"

    if payload.auto_ingest:
        checksum = compute_sha256(tx_path)
        job = IngestionJob(
            id=job_id,
            source_file=tx_path.name,
            file_format=payload.file_format,
            file_checksum=checksum,
            status="QUEUED",
            records_received=payload.num_records,
            triggered_by=current_user.username,
            backend_target="bigquery" if settings.is_bigquery_mode else "local",
        )
        db.add(job)
        record_audit_log(
            db,
            actor=current_user.username,
            actor_role=current_user.role,
            action="SYNTHETIC_DATASET_GENERATED",
            resource_type="ingestion_job",
            resource_id=job_id,
            updated_value=f"records={payload.num_records}, seed={payload.seed}, file={tx_path.name}",
        )
        db.commit()

        background_tasks.add_task(
            execute_etl_job,
            job_id=job_id,
            file_path=tx_path,
            triggered_by=current_user.username,
            customers_file=gen_res["customers_file"],
            accounts_file=gen_res["accounts_file"],
            merchants_file=gen_res["merchants_file"],
        )

    return {
        "job_id": job_id if payload.auto_ingest else None,
        "status": "QUEUED" if payload.auto_ingest else "GENERATED_ONLY",
        "files": gen_res["manifest"]["files"],
        "manifest_file": gen_res["manifest_file"],
        "manifest_summary": {
            "num_records": gen_res["manifest"]["num_records"],
            "synthetic_fraud_count": gen_res["manifest"]["synthetic_fraud_count"],
            "total_injected_issues": gen_res["manifest"]["total_injected_issues"],
            "injected_quality_issues_summary": gen_res["manifest"]["injected_quality_issues_summary"],
        },
    }


@router.get("/jobs")
def list_ingestion_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent ETL ingestion jobs with processing metrics."""
    jobs = db.query(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(50).all()
    return [
        {
            "job_id": j.id,
            "source_file": j.source_file,
            "file_format": j.file_format,
            "file_checksum": j.file_checksum,
            "status": j.status,
            "records_received": j.records_received,
            "records_processed": j.records_processed,
            "valid_records": j.valid_records,
            "invalid_records": j.invalid_records,
            "duplicate_records": j.duplicate_records,
            "quarantined_records": j.quarantined_records,
            "processing_duration_sec": j.processing_duration_sec,
            "idempotent_skip": j.idempotent_skip,
            "failure_reason": j.failure_reason,
            "triggered_by": j.triggered_by,
            "backend_target": j.backend_target,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
def get_ingestion_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed status and metrics for a specific ETL ingestion job."""
    j = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    return {
        "job_id": j.id,
        "source_file": j.source_file,
        "file_format": j.file_format,
        "file_checksum": j.file_checksum,
        "status": j.status,
        "records_received": j.records_received,
        "records_processed": j.records_processed,
        "valid_records": j.valid_records,
        "invalid_records": j.invalid_records,
        "duplicate_records": j.duplicate_records,
        "quarantined_records": j.quarantined_records,
        "processing_duration_sec": j.processing_duration_sec,
        "idempotent_skip": j.idempotent_skip,
        "failure_reason": j.failure_reason,
        "triggered_by": j.triggered_by,
        "backend_target": j.backend_target,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "completed_at": j.completed_at.isoformat() if j.completed_at else None,
    }
