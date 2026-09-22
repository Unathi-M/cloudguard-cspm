# Initial Scan Notes

## Scan date

2026-09-22

## Scanned directory

terraform/insecure

## Scanner

Checkov 3.3.19

## Terraform validation

The configuration passed Terraform validation.

## Configuration

The configuration is intentionally insecure and is not deployed.

## Expected security weaknesses

- Public S3 bucket access
- Missing S3 encryption
- Missing S3 access logging
- Open SSH access
- Open HTTP access
- Overly permissive IAM policy
- Missing resource tags

## Initial results

- Passed checks: 9
- Failed checks: 25
- Skipped checks: 0

## Observations

The initial scan is expected to identify multiple security misconfigurations involving storage, IAM, and network exposure.
