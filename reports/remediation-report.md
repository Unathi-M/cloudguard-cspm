# Remediation Report

## Project

CloudGuard CSPM Dashboard

## Scope

This assessment compares two local Terraform configurations:

- `terraform/insecure`
- `terraform/remediated`

The configurations were scanned with Checkov. Neither configuration was deployed to AWS.

## Scanner

- Tool: Checkov
- Version: 3.3.19
- Scan type: Terraform static analysis

## Remediation objectives

The remediation focused on:

- Preventing public S3 access
- Enabling encryption at rest
- Enabling S3 versioning
- Restricting administrative SSH access
- Replacing wildcard IAM permissions
- Adding resource tags
- Reducing unrestricted outbound access

## Results

| Metric         | Insecure configuration | Remediated configuration | Change |
| -------------- | ---------------------: | -----------------------: | -----: |
| Passed checks  |                      9 |                       18 |     +9 |
| Failed checks  |                     25 |                        7 |    -18 |
| Skipped checks |                      0 |                        0 |      0 |

## Assessment summary

The remediated configuration reduced failed Checkov checks from 25 to 7, an improvement of 18 failed checks. Passed checks increased from 9 to 18.

This demonstrates that preventive infrastructure scanning can identify cloud security weaknesses before deployment and that targeted remediation can measurably improve the security posture of infrastructure-as-code.

The remaining seven findings require additional review. They should not automatically be treated as defects because some may reflect limitations of this simplified local lab, context-dependent controls, or production requirements not currently represented in the configuration.

## Key remediations

### Storage security

Public access controls were enabled for the S3 bucket. Server-side encryption and versioning were also configured.

### Identity and access management

The wildcard IAM policy was replaced with a narrowly scoped read-only policy for the specific S3 bucket and its objects.

### Network security

SSH access was restricted from the entire internet to a documentation-only administrative CIDR. Egress was limited to HTTPS for this lab.

### Resource governance

Common tags were added to support ownership, environment identification, and asset inventory.

## Remaining findings

| Check ID    | Finding                                                   | Resource                        | Classification              | Explanation                                                                                                                                               |
| ----------- | --------------------------------------------------------- | ------------------------------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CKV_AWS_260 | Security group allows ingress from `0.0.0.0/0` to port 80 | `aws_security_group.secure_web` | Context-dependent           | Public HTTP may be required for a public web service, although HTTPS should be preferred in production.                                                   |
| CKV2_AWS_62 | S3 event notifications are not enabled                    | `aws_s3_bucket.customer_data`   | Future enhancement          | Event notifications were outside the scope of this initial storage-security lab. They could support monitoring and automated response workflows.          |
| CKV_AWS_18  | S3 access logging is not enabled                          | `aws_s3_bucket.customer_data`   | Remediate in next iteration | Access logging should be enabled for auditability and investigation. It was not included in the current remediated configuration.                         |
| CKV2_AWS_61 | S3 lifecycle configuration is not defined                 | `aws_s3_bucket.customer_data`   | Future enhancement          | Lifecycle rules should be added to manage retention, archival, and deletion of object versions.                                                           |
| CKV_AWS_144 | S3 cross-region replication is not enabled                | `aws_s3_bucket.customer_data`   | Context-dependent           | Replication depends on availability, disaster-recovery, and data-residency requirements. It is not necessary for this small local lab.                    |
| CKV2_AWS_5  | Security group is not attached to another resource        | `aws_security_group.secure_web` | Accepted limitation         | The lab defines the security group for static analysis but does not create an EC2 instance or other workload to attach it to.                             |
| CKV_AWS_145 | S3 bucket is not encrypted with AWS KMS                   | `aws_s3_bucket.customer_data`   | Future enhancement          | The lab uses AES-256 S3-managed encryption. KMS encryption would provide stronger key-management and auditing capabilities for sensitive production data. |

The remaining findings were reviewed individually rather than suppressed. One finding is a network-design decision, one reflects the absence of a deployed workload in the static-analysis lab, and the remaining findings are future enhancements involving logging, notifications, lifecycle management, replication, and KMS-based encryption.


### Classification meanings

- **Remediate now:** The issue can be fixed in the current lab.
- **Accepted limitation:** The issue is outside the current project scope.
- **Context-dependent:** The result depends on the real deployment environment.
- **Future enhancement:** The issue will be addressed in a later version.

## Lessons learned

The comparison demonstrates that security controls should be evaluated before infrastructure is deployed. Public exposure, excessive IAM permissions, missing encryption, and insufficient governance can be detected directly from infrastructure-as-code.

The result also shows that remediation should be measured rather than assumed. In this lab, failed findings decreased from 25 to 7, while passed checks increased from 9 to 18.
