@"
# CloudGuard CSPM Dashboard

CloudGuard is a local cloud security posture management dashboard that identifies and prioritizes security misconfigurations in Terraform infrastructure code.

## Project objective

This project demonstrates how a Cloud Security Analyst can:

- Review infrastructure-as-code
- Detect cloud security misconfigurations
- Prioritize findings by risk
- Recommend remediation
- Compare insecure and remediated configurations
- Present findings through a dashboard

## Current scope

The current implementation scans Terraform configurations using Checkov. It includes:

- An intentionally insecure Terraform environment
- A remediated Terraform environment
- Raw Checkov JSON output
- Normalized security findings
- Category and severity classification
- Explainable risk scoring
- Automated tests

## Architecture

```text
Terraform configurations
          ↓
Checkov scanner
          ↓
Raw JSON findings
          ↓
Python normalizer
          ↓
SQLite database
          ↓
Streamlit dashboard

## Findings normalization

Checkov produces scanner-specific JSON output. The project normalizes failed checks into a consistent finding model containing category, severity, risk score, environment, resource, source location, and remediation guidance.

The normalizer can process both:

- `data/raw/insecure-findings.json`
- `data/raw/remediated-findings.json`

The severity values are portfolio-level heuristic ratings, not official AWS or Checkov ratings. The project documents the heuristic so that the scoring is transparent and reproducible.

## SQLite database

Normalized findings are loaded into a local SQLIte database at:

```text
data/cloudguard.db

## Continuous security validation

GitHub Actions validates the project on pushes to `main` and on pull requests.

The workflow:

- Runs the Python test suite
- Verifies Terraform formatting
- Scans remediated Terraform with Checkov
- Scans the intentionally insecure baseline for demonstration

The insecure baseline is intentionally vulnerable and is configured as an informational scan. The remediated configuration is used as the security-quality gate.

## CI security-gate decision

Checkov scans for both Terraform environments currently run as informational CI steps.

The insecure environment is intentionally vulnerable and is included to demonstrate baseline detection. The remediated environment has reduced failed checks from 25 to 7, but the remaining findings are documented in `reports/remediation-report.md`.

The Python test suite and Terraform formatting checks remain blocking quality gates. As the remediated configuration improves, the Checkov scan can later be converted into a required security gate.
