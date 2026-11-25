"""CLI script to load CSV/JSON into BigQuery and run dry-run cost estimation."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.core.config import get_settings  # noqa: E402
from backend.app.services.gcp_service import GCPIntegrationService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch load local CSV/JSON to BigQuery or run dry-run SQL estimate.")
    parser.add_argument("--file", help="Path to local CSV or JSON file to load into finguard_raw.")
    parser.add_argument("--table", default="transactions_raw", help="Target BigQuery table name.")
    parser.add_argument("--dry-run-sql", help="Optional path to SQL file for dry-run cost estimation.")
    args = parser.parse_args()

    settings = get_settings()
    svc = GCPIntegrationService()

    if args.file:
        fmt = "JSON" if args.file.lower().endswith(".json") else "CSV"
        res = svc.load_file_to_bigquery(args.file, settings.BIGQUERY_RAW_DATASET, args.table, source_format=fmt)
        print("[OK] BigQuery load completed:", res)

    if args.dry_run_sql:
        sql_text = Path(args.dry_run_sql).read_text(encoding="utf-8")
        est = svc.estimate_query_cost(sql_text)
        print("[OK] BigQuery dry-run cost estimation:", est)


if __name__ == "__main__":
    main()
