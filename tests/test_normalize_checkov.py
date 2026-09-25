from scanners.normalize_checkov import (
    calculate_risk_score,
    classify_category,
    classify_severity,
)


def test_public_s3_finding_is_storage():
    category = classify_category(
        "Ensure S3 bucket is not publicly accessible",
        "aws_s3_bucket.customer_data",
    )

    assert category == "Storage"


def test_open_network_finding_is_high_severity():
    severity = classify_severity(
        "Ensure no security groups allow ingress from 0.0.0.0/0",
        "aws_security_group.secure_web",
    )

    assert severity == "HIGH"


def test_iam_policy_finding_is_high_severity():
    severity = classify_severity(
        "IAM policy grants wildcard permissions",
        "aws_iam_policy.insecure_admin_policy",
    )

    assert severity == "HIGH"


def test_risk_score_is_positive_for_high_storage_finding():
    score = calculate_risk_score(
        severity="HIGH",
        category="Storage",
        resource="aws_s3_bucket.customer_data",
    )

    assert score > 0


def test_unknown_category_falls_back_to_other():
    category = classify_category(
        "Ensure a special custom control is configured",
        "custom_resource.example",
    )

    assert category == "Other"
