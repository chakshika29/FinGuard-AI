"""CLI script to provision FinGuard AI BigQuery datasets and partitioned/clustered tables.

Usage:
    python cloud/gcp/setup_gcp_resources.py
Requires GCP_PROJECT_ID and valid ADC or GOOGLE_APPLICATION_CREDENTIALS in .env.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.services.gcp_service import GCPIntegrationService  # noqa: E402


def main() -> None:
    svc = GCPIntegrationService()
    status = svc.check_connection()
    if not status.get("verified"):
        print(f"[INFO] GCP connection not active: {status.get('message')}")
        print("[INFO] Set GCP_PROJECT_ID and authenticate via `gcloud auth application-default login`.")
        sys.exit(1)

    datasets = svc.ensure_datasets_exist()
    print("[OK] BigQuery datasets ready:")
    for ds in datasets:
        print(f"  - {ds}")

    table_id = svc.ensure_partitioned_curated_table()
    print(f"[OK] Partitioned & clustered table ready: {table_id}")


if __name__ == "__main__":
    main()
