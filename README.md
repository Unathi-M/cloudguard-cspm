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
