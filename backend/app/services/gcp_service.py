"""Genuine Google Cloud Platform (BigQuery & Cloud Storage) integration service.

Uses official google-cloud-bigquery and google-cloud-storage SDKs.
Supports Application Default Credentials (ADC) or service account JSON via
GOOGLE_APPLICATION_CREDENTIALS, dry-run query cost estimation, partitioned and
clustered BigQuery tables, and GCS raw file uploads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery, storage

from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

# BigQuery on-demand query pricing approximation: $6.25 per TiB (1,099,511,627,776 bytes)
BQ_PRICE_PER_TIB_USD = 6.25


class GCPIntegrationService:
    """Wrapper around official Google Cloud BigQuery and GCS Python clients."""

    def __init__(self, project_id: str | None = None, location: str | None = None, bucket_name: str | None = None):
        settings = get_settings()
        self.project_id = project_id if project_id is not None else settings.GCP_PROJECT_ID
        self.location = location if location is not None else settings.GCP_LOCATION
        self.bucket_name = bucket_name if bucket_name is not None else settings.GCS_BUCKET_NAME
        self._bq_client: bigquery.Client | None = None
        self._gcs_client: storage.Client | None = None

    def is_configured(self) -> bool:
        return bool(self.project_id)

    def get_bq_client(self) -> bigquery.Client:
        if not self.project_id:
            raise RuntimeError("GCP_PROJECT_ID is not configured.")
        if self._bq_client is None:
            self._bq_client = bigquery.Client(project=self.project_id, location=self.location)
        return self._bq_client

    def get_gcs_client(self) -> storage.Client:
        if not self.project_id:
            raise RuntimeError("GCP_PROJECT_ID is not configured.")
        if self._gcs_client is None:
            self._gcs_client = storage.Client(project=self.project_id)
        return self._gcs_client

    def check_connection(self) -> dict[str, Any]:
        """Verify whether GCP credentials and project are configured and reachable."""
        if not self.is_configured():
            return {
                "configured": False,
                "verified": False,
                "mode": "local",
                "message": "GCP_PROJECT_ID is empty. Operating in Local Mode (DuckDB).",
            }
        try:
            client = self.get_bq_client()
            datasets = [ds.dataset_id for ds in client.list_datasets(max_results=10)]
            return {
                "configured": True,
                "verified": True,
                "mode": "bigquery",
                "project_id": self.project_id,
                "location": self.location,
                "datasets_found": datasets,
            }
        except DefaultCredentialsError as exc:
            return {
                "configured": True,
                "verified": False,
                "mode": "local",
                "message": f"GCP credentials not found (ADC): {exc}",
            }
        except Exception as exc:
            return {
                "configured": True,
                "verified": False,
                "mode": "local",
                "message": f"GCP connection check failed: {exc}",
            }

    def ensure_datasets_exist(self) -> list[str]:
        """Create the 5-layer BigQuery datasets if they do not exist."""
        settings = get_settings()
        client = self.get_bq_client()
        dataset_names = [
            settings.BIGQUERY_RAW_DATASET,
            settings.BIGQUERY_STAGING_DATASET,
            settings.BIGQUERY_CURATED_DATASET,
            settings.BIGQUERY_GOVERNANCE_DATASET,
            settings.BIGQUERY_ANALYTICS_DATASET,
        ]
        created: list[str] = []
        for name in dataset_names:
            ds_id = f"{self.project_id}.{name}"
            dataset = bigquery.Dataset(ds_id)
            dataset.location = self.location
            client.create_dataset(dataset, exists_ok=True)
            created.append(ds_id)
        return created

    def ensure_partitioned_curated_table(self) -> str:
        """Create partitioned & clustered curated transactions table in BigQuery."""
        settings = get_settings()
        client = self.get_bq_client()
        table_id = f"{self.project_id}.{settings.BIGQUERY_CURATED_DATASET}.transactions"
        schema = [
            bigquery.SchemaField("transaction_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("account_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("card_token", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("transaction_timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("transaction_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("transaction_amount", "FLOAT64", mode="REQUIRED"),
            bigquery.SchemaField("currency", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("merchant_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("merchant_category", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("transaction_type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("payment_method", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("transaction_country", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("transaction_city", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("device_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("transaction_status", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("credit_limit", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("outstanding_balance", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("repayment_status", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("customer_risk_category", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("fraud_label", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("ingestion_timestamp", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("source_system", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("ingestion_job_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("fraud_risk_score", "FLOAT64", mode="NULLABLE"),
            bigquery.SchemaField("fraud_risk_level", "STRING", mode="NULLABLE"),
        ]
        table = bigquery.Table(table_id, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="transaction_date",
        )
        table.clustering_fields = ["transaction_country", "merchant_category", "fraud_risk_level"]
        client.create_table(table, exists_ok=True)
        return table_id

    def upload_file_to_gcs(self, local_path: str | Path, destination_blob: str) -> str:
        """Upload raw CSV or JSON file to Google Cloud Storage bucket."""
        if not self.bucket_name:
            raise RuntimeError("GCS_BUCKET_NAME is not configured.")
        client = self.get_gcs_client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob(destination_blob)
        blob.upload_from_filename(str(local_path))
        return f"gs://{self.bucket_name}/{destination_blob}"

    def load_file_to_bigquery(
        self,
        local_path: str | Path,
        dataset_name: str,
        table_name: str,
        source_format: str = "CSV",
        write_disposition: str = "WRITE_APPEND",
    ) -> dict[str, Any]:
        """Batch load a CSV or newline-delimited JSON file directly into BigQuery."""
        client = self.get_bq_client()
        table_id = f"{self.project_id}.{dataset_name}.{table_name}"
        fmt = (
            bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
            if source_format.upper() == "JSON"
            else bigquery.SourceFormat.CSV
        )
        job_config = bigquery.LoadJobConfig(
            source_format=fmt,
            autodetect=True,
            skip_leading_rows=1 if fmt == bigquery.SourceFormat.CSV else 0,
            write_disposition=write_disposition,
        )
        with Path(local_path).open("rb") as f:
            load_job = client.load_table_from_file(f, table_id, job_config=job_config)
        load_job.result()
        dest_table = client.get_table(table_id)
        return {
            "job_id": load_job.job_id,
            "table_id": table_id,
            "output_rows": dest_table.num_rows,
            "state": load_job.state,
        }

    def estimate_query_cost(self, sql: str) -> dict[str, Any]:
        """Execute a BigQuery dry-run to estimate bytes processed and query cost without executing."""
        client = self.get_bq_client()
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = client.query(sql, job_config=job_config)
        bytes_processed = int(query_job.total_bytes_processed or 0)
        tib = bytes_processed / (1024 ** 4)
        est_usd = round(tib * BQ_PRICE_PER_TIB_USD, 6)
        return {
            "dry_run": True,
            "total_bytes_processed": bytes_processed,
            "total_mb_processed": round(bytes_processed / (1024 ** 2), 4),
            "estimated_cost_usd": est_usd,
            "within_free_tier_1tb": bytes_processed <= (1024 ** 4),
        }

    def execute_query(self, sql: str) -> list[dict[str, Any]]:
        """Run a BigQuery SQL query and return rows as dictionaries."""
        client = self.get_bq_client()
        query_job = client.query(sql)
        results = query_job.result()
        return [dict(row.items()) for row in results]
