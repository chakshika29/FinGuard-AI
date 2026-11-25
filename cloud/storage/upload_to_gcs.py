"""CLI script to upload synthetic raw files to Google Cloud Storage."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.services.gcp_service import GCPIntegrationService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload raw transaction file to GCS.")
    parser.add_argument("--file", required=True, help="Path to local CSV or JSON file.")
    parser.add_argument("--prefix", default="raw/transactions", help="Destination GCS folder prefix.")
    args = parser.parse_args()

    local_path = Path(args.file)
    if not local_path.exists():
        print(f"[ERROR] File not found: {local_path}")
        sys.exit(1)

    svc = GCPIntegrationService()
    blob_name = f"{args.prefix.rstrip('/')}/{local_path.name}"
    gs_uri = svc.upload_file_to_gcs(local_path, blob_name)
    print(f"[OK] Uploaded to {gs_uri}")


if __name__ == "__main__":
    main()
