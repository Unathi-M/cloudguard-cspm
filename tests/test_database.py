import json
import sqlite3

from dashboard.database import (
    create_schema,
    fetch_all_findings,
    fetch_summary,
    seed_findings,
)


def sample_findings():
    return [
        {
            "finding_key": "insecure:TEST001:aws_s3_bucket.example",
            "check_id": "TEST001",
            "title": "Test storage finding",
            "description": "A test finding.",
            "severity": "HIGH",
            "category": "Storage",
            "resource": "aws_s3_bucket.example",
            "file": "terraform/main.tf",
            "line": "1-5",
            "status": "OPEN",
            "environment": "insecure",
            "scanner": "Checkov",
            "risk_score": 42,
            "recommendation": "Protect the bucket.",
            "first_seen": "2026-09-25T00:00:00+00:00",
        }
    ]


def test_database_schema_is_created(tmp_path):
    database_path = tmp_path / "test.db"

    create_schema(database_path)

    connection = sqlite3.connect(database_path)
    tables = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()
    connection.close()

    assert ("findings",) in tables
    assert ("scan_runs",) in tables


def test_seed_loads_findings(tmp_path):
    database_path = tmp_path / "test.db"
    input_path = tmp_path / "findings.json"
    input_path.write_text(
        json.dumps(sample_findings()),
        encoding="utf-8",
    )

    scan_run_id, count = seed_findings(
        input_path=input_path,
        environment="insecure",
        database_path=database_path,
    )

    assert scan_run_id == 1
    assert count == 1


def test_summary_counts_findings(tmp_path):
    database_path = tmp_path / "test.db"
    input_path = tmp_path / "findings.json"
    input_path.write_text(
        json.dumps(sample_findings()),
        encoding="utf-8",
    )

    seed_findings(
        input_path=input_path,
        environment="insecure",
        database_path=database_path,
    )

    summary = fetch_summary(database_path)

    assert summary["total"] == 1
    assert summary["open"] == 1
    assert summary["high_or_critical"] == 1


def test_duplicate_seed_does_not_duplicate_findings(tmp_path):
    database_path = tmp_path / "test.db"
    input_path = tmp_path / "findings.json"
    input_path.write_text(
        json.dumps(sample_findings()),
        encoding="utf-8",
    )

    seed_findings(
        input_path=input_path,
        environment="insecure",
        database_path=database_path,
    )

    seed_findings(
        input_path=input_path,
        environment="insecure",
        database_path=database_path,
    )

    rows = fetch_all_findings(database_path)

    assert len(rows) == 1
