"""Load normalized CloudGuard findings into SQLite."""

from __future__ import annotations

import argparse
from pathlib import Path

from database import DEFAULT_DATABASE_PATH, seed_findings


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Seed the CloudGuard SQLite database."
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to normalized findings JSON.",
    )

    parser.add_argument(
        "--environment",
        required=True,
        choices=("insecure", "remediated"),
        help="Environment represented by the input file.",
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="SQLite database path.",
    )

    return parser.parse_args()


def main() -> None:
    """Load one normalized findings file into SQLite."""
    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Normalized findings file not found: {args.input}"
        )

    if args.input.is_dir():
        raise IsADirectoryError(
            f"Input path is a directory, not a file: {args.input}"
        )

    scan_run_id, finding_count = seed_findings(
        input_path=args.input,
        environment=args.environment,
        database_path=args.database,
    )

    print(f"Scan run created: {scan_run_id}")
    print(f"Findings loaded: {finding_count}")
    print(f"Database: {args.database}")


if __name__ == "__main__":
    main()
