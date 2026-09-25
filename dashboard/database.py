"""SQLite database helpers for the CloudGuard CSPM dashboard."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


DEFAULT_DATABASE_PATH = Path("data/cloudguard.db")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scan_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    environment TEXT NOT NULL,
    scanner TEXT NOT NULL,
    total_findings INTEGER NOT NULL,
    critical_count INTEGER NOT NULL DEFAULT 0,
    high_count INTEGER NOT NULL DEFAULT 0,
    medium_count INTEGER NOT NULL DEFAULT 0,
    low_count INTEGER NOT NULL DEFAULT 0,
    scan_time TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_key TEXT NOT NULL UNIQUE,
    check_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    category TEXT NOT NULL,
    resource TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line TEXT NOT NULL,
    status TEXT NOT NULL,
    environment TEXT NOT NULL,
    scanner TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    recommendation TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_findings_environment
    ON findings(environment);

CREATE INDEX IF NOT EXISTS idx_findings_severity
    ON findings(severity);

CREATE INDEX IF NOT EXISTS idx_findings_category
    ON findings(category);

CREATE INDEX IF NOT EXISTS idx_findings_status
    ON findings(status);
"""


def get_connection(database_path: Path = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    """Open a SQLite connection and return rows as dictionary-like objects."""
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    return connection


def create_schema(database_path: Path = DEFAULT_DATABASE_PATH) -> None:
    """Create database tables and indexes if they do not exist."""
    with get_connection(database_path) as connection:
        connection.executescript(SCHEMA_SQL)


def load_findings(input_path: Path) -> list[dict[str, Any]]:
    """Load a normalized findings JSON array."""
    with input_path.open("r", encoding="utf-8-sig") as input_file:
        findings = json.load(input_file)

    if not isinstance(findings, list):
        raise ValueError("Normalized findings file must contain a JSON array.")

    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("Each normalized finding must be a JSON object.")

    return findings


def count_severities(findings: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Count findings by severity."""
    counts = {
        "CRITICAL": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
    }

    for finding in findings:
        severity = str(finding.get("severity", "LOW")).upper()
        counts[severity] = counts.get(severity, 0) + 1

    return counts


def insert_scan_run(
    connection: sqlite3.Connection,
    findings: list[dict[str, Any]],
    environment: str,
    scanner: str = "Checkov",
) -> int:
    """Insert one scan-run summary and return its database ID."""
    if findings:
        scan_time = findings[0].get("first_seen", "")
    else:
        scan_time = ""

    severity_counts = count_severities(findings)

    cursor = connection.execute(
        """
        INSERT INTO scan_runs (
            environment,
            scanner,
            total_findings,
            critical_count,
            high_count,
            medium_count,
            low_count,
            scan_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            environment,
            scanner,
            len(findings),
            severity_counts.get("CRITICAL", 0),
            severity_counts.get("HIGH", 0),
            severity_counts.get("MEDIUM", 0),
            severity_counts.get("LOW", 0),
            scan_time,
        ),
    )

    return int(cursor.lastrowid)


def upsert_findings(
    connection: sqlite3.Connection,
    findings: list[dict[str, Any]],
) -> None:
    """Insert findings or update existing findings with the same finding key."""
    for finding in findings:
        connection.execute(
            """
            INSERT INTO findings (
                finding_key,
                check_id,
                title,
                description,
                severity,
                category,
                resource,
                file_path,
                line,
                status,
                environment,
                scanner,
                risk_score,
                recommendation,
                first_seen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(finding_key) DO UPDATE SET
                check_id = excluded.check_id,
                title = excluded.title,
                description = excluded.description,
                severity = excluded.severity,
                category = excluded.category,
                resource = excluded.resource,
                file_path = excluded.file_path,
                line = excluded.line,
                status = excluded.status,
                environment = excluded.environment,
                scanner = excluded.scanner,
                risk_score = excluded.risk_score,
                recommendation = excluded.recommendation,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                finding.get("finding_key", ""),
                finding.get("check_id", ""),
                finding.get("title", ""),
                finding.get("description", ""),
                finding.get("severity", "LOW"),
                finding.get("category", "Other"),
                finding.get("resource", ""),
                finding.get("file", ""),
                str(finding.get("line", "")),
                finding.get("status", "OPEN"),
                finding.get("environment", ""),
                finding.get("scanner", "Checkov"),
                int(finding.get("risk_score", 0)),
                finding.get("recommendation", ""),
                finding.get("first_seen", ""),
            ),
        )


def seed_findings(
    input_path: Path,
    environment: str,
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> tuple[int, int]:
    """
    Load findings into SQLite.

    Returns:
        A tuple containing scan-run ID and finding count.
    """
    findings = load_findings(input_path)
    create_schema(database_path)

    with get_connection(database_path) as connection:
        scan_run_id = insert_scan_run(
            connection=connection,
            findings=findings,
            environment=environment,
        )
        upsert_findings(connection, findings)

    return scan_run_id, len(findings)


def fetch_all_findings(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> list[sqlite3.Row]:
    """Return all findings ordered by descending risk score."""
    create_schema(database_path)

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM findings
            ORDER BY risk_score DESC, severity ASC, title ASC
            """
        ).fetchall()

    return rows


def fetch_summary(
    database_path: Path = DEFAULT_DATABASE_PATH,
) -> dict[str, int]:
    """Return high-level finding counts."""
    create_schema(database_path)

    with get_connection(database_path) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM findings"
        ).fetchone()[0]

        open_count = connection.execute(
            "SELECT COUNT(*) FROM findings WHERE status = 'OPEN'"
        ).fetchone()[0]

        high_or_critical = connection.execute(
            """
            SELECT COUNT(*)
            FROM findings
            WHERE severity IN ('CRITICAL', 'HIGH')
            """
        ).fetchone()[0]

    return {
        "total": int(total),
        "open": int(open_count),
        "high_or_critical": int(high_or_critical),
    }
