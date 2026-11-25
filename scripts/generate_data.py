"""CLI script to generate synthetic financial datasets (10k, 100k, 1M+)."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.pipelines.generator import generate_synthetic_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic FinGuard AI financial datasets.")
    parser.add_argument("--records", type=int, default=100000, help="Number of synthetic transaction records.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output transaction file format.")
    parser.add_argument("--output-dir", default="data/raw", help="Destination directory.")
    parser.add_argument("--issue-rate", type=float, default=0.03, help="Rate of injected data quality problems.")
    args = parser.parse_args()

    res = generate_synthetic_dataset(
        num_records=args.records,
        seed=args.seed,
        output_dir=args.output_dir,
        file_format=args.format,
        quality_issue_rate=args.issue_rate,
    )
    print("[OK] Synthetic dataset generated:")
    print(f"  Transactions: {res['transactions_file']}")
    print(f"  Manifest:     {res['manifest_file']}")
    print(f"  Fraud Count:  {res['manifest']['synthetic_fraud_count']}")
    print(f"  Issues Count: {res['manifest']['total_injected_issues']}")


if __name__ == "__main__":
    main()
