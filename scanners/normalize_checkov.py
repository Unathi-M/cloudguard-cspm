"""Normalize Checkov JSON output for the CloudGuard CSPM dashboard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "IAM": (
        "iam",
        "policy",
        "permission",
        "role",
        "user",
        "privilege",
        "access key",
    ),
    "Storage": (
        "s3",
        "bucket",
        "storage",
        "lifecycle",
        "replication",
        "object",
    ),
    "Network": (
        "security group",
        "network",
        "vpc",
        "port",
        "ingress",
        "egress",
        "firewall",
    ),
    "Logging": (
        "logging",
        "log",
        "cloudtrail",
        "monitoring",
        "notification",
        "event",
    ),
    "Encryption": (
        "encrypt",
        "kms",
        "ssl",
        "tls",
    ),
    "Governance": (
        "tag",
        "metadata",
        "naming",
        "owner",
    ),
}


RECOMMENDATIONS: dict[str, str] = {
    "IAM": (
        "Apply least privilege and restrict permissions to only the required "
        "actions and resources."
    ),
    "Storage": (
        "Block public access, enable appropriate encryption, configure "
        "retention controls, and protect stored data."
    ),
    "Network": (
        "Restrict network exposure to approved sources and avoid unnecessary "
        "open ports."
    ),
    "Logging": (
        "Enable centralized logging, event monitoring, and retention of "
        "security-relevant activity."
    ),
    "Encryption": (
        "Enable encryption at rest and in transit using an approved "
        "key-management approach."
    ),
    "Governance": (
        "Add ownership, environment, and data-classification metadata."
    ),
    "Other": (
        "Review the Checkov guidance and apply the appropriate security "
        "control."
    ),
}


SEVERITY_SCORES: dict[str, int] = {
    "CRITICAL": 10,
    "HIGH": 7,
    "MEDIUM": 4,
    "LOW": 1,
    "INFO": 0,
}


def get_field(
    item: dict[str, Any],
    *field_names: str,
    default: Any = "",
) -> Any:
    """Return the first non-empty value from the supplied field names."""
    for field_name in field_names:
        value = item.get(field_name)
        if value not in (None, ""):
            return value

    return default


def classify_category(check_name: str, resource: str) -> str:
    """Assign a broad security category using the check and resource text."""
    searchable_text = f"{check_name} {resource}".lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in searchable_text for keyword in keywords):
            return category

    return "Other"


def classify_severity(check_name: str, resource: str) -> str:
    """
    Assign a portfolio-level severity.

    Checkov does not consistently provide severity for every Terraform check,
    so this project uses a transparent heuristic that can be improved later.
    """
    searchable_text = f"{check_name} {resource}".lower()

    critical_keywords = (
        "root access",
        "administratoraccess",
        "full administrative",
    )

    high_keywords = (
        "public",
        "wildcard",
        "admin",
        "unrestricted",
        "0.0.0.0/0",
        "open to the world",
        "anonymous",
    )

    medium_keywords = (
        "logging",
        "monitoring",
        "versioning",
        "tag",
        "encryption",
        "lifecycle",
        "replication",
        "notification",
    )

    if any(keyword in searchable_text for keyword in critical_keywords):
        return "CRITICAL"

    if any(keyword in searchable_text for keyword in high_keywords):
        return "HIGH"

    if any(keyword in searchable_text for keyword in medium_keywords):
        return "MEDIUM"

    return "LOW"


def calculate_risk_score(
    severity: str,
    category: str,
    resource: str,
) -> int:
    """
    Calculate a simple explainable risk score.

    Risk score = severity score × exposure factor × asset importance.
    """
    severity_score = SEVERITY_SCORES[severity]

    exposure_factor = 3 if category in {"IAM", "Network", "Storage"} else 2

    important_resource_text = f"{resource} {category}".lower()
    asset_importance = (
        3
        if any(
            keyword in important_resource_text
            for keyword in ("customer", "data", "iam", "policy")
        )
        else 1
    )

    return severity_score * exposure_factor * asset_importance


def normalize_check(
    item: dict[str, Any],
    environment: str,
    scan_timestamp: str,
) -> dict[str, Any]:
    """Convert one Checkov failed check into a normalized finding."""
    check_id = get_field(
        item,
        "check_id",
        "checkId",
        default="UNKNOWN",
    )

    check_name = get_field(
        item,
        "check_name",
        "checkName",
        "name",
        default="Unnamed security check",
    )

    resource = get_field(
        item,
        "resource",
        "resource_address",
        default="Unknown resource",
    )

    file_path = get_field(
        item,
        "file_path",
        "file",
        default="",
    )

    file_line_range = get_field(
        item,
        "file_line_range",
        "file_line",
        default="",
    )

    category = classify_category(check_name, resource)
    severity = classify_severity(check_name, resource)
    risk_score = calculate_risk_score(
        severity=severity,
        category=category,
        resource=resource,
    )

    return {
        "finding_key": f"{environment}:{check_id}:{resource}",
        "check_id": check_id,
        "title": check_name,
        "description": (
            f"Checkov identified a potential {category.lower()} "
            "security issue."
        ),
        "severity": severity,
        "category": category,
        "resource": resource,
        "file": file_path,
        "line": file_line_range,
        "status": "OPEN",
        "environment": environment,
        "scanner": "Checkov",
        "risk_score": risk_score,
        "recommendation": RECOMMENDATIONS.get(
            category,
            RECOMMENDATIONS["Other"],
        ),
        "first_seen": scan_timestamp,
    }


def load_checkov_results(input_path: Path) -> dict[str, Any]:
    """Load a Checkov JSON file, supporting UTF-8 BOM files."""
    with input_path.open("r", encoding="utf-8-sig") as input_file:
        document = json.load(input_file)

    if not isinstance(document, dict):
        raise ValueError("Checkov JSON must contain a top-level object.")

    return document


def extract_failed_checks(document: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract failed checks from standard Checkov output.

    The current project produces one top-level result object. This function
    also gives us a clear place to support additional Checkov formats later.
    """
    results = document.get("results", {})

    if not isinstance(results, dict):
        raise ValueError("The Checkov 'results' field is not an object.")

    failed_checks = results.get("failed_checks", [])

    if not isinstance(failed_checks, list):
        raise ValueError("The Checkov failed_checks field is not a list.")

    return [
        item for item in failed_checks
        if isinstance(item, dict)
    ]


def normalize_file(
    input_path: Path,
    output_path: Path,
    environment: str,
) -> None:
    """Normalize one Checkov input file and write a JSON array."""
    document = load_checkov_results(input_path)
    failed_checks = extract_failed_checks(document)

    scan_timestamp = datetime.now(timezone.utc).isoformat()

    normalized_findings = [
        normalize_check(
            item=item,
            environment=environment,
            scan_timestamp=scan_timestamp,
        )
        for item in failed_checks
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(normalized_findings, output_file, indent=2)

    print(f"Normalized findings: {len(normalized_findings)}")
    print(f"Environment: {environment}")
    print(f"Output: {output_path}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Normalize Checkov findings for CloudGuard CSPM."
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the raw Checkov JSON file.",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path for normalized JSON output.",
    )

    parser.add_argument(
        "--environment",
        required=True,
        choices=("insecure", "remediated"),
        help="Environment represented by the scan.",
    )

    return parser.parse_args()


def main() -> None:
    """Run the normalizer."""
    args = parse_arguments()

    if not args.input.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {args.input}"
        )

    if args.input.is_dir():
        raise IsADirectoryError(
            f"Input path is a directory, not a JSON file: {args.input}"
        )

    normalize_file(
        input_path=args.input,
        output_path=args.output,
        environment=args.environment,
    )


if __name__ == "__main__":
    main()
