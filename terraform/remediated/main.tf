terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  common_tags = {
    Project     = "CloudGuard CSPM"
    Environment = "portfolio-lab"
    ManagedBy   = "Terraform"
    Owner       = "Cloud Security Team"
  }
}

resource "aws_s3_bucket" "customer_data" {
  bucket = "cloudguard-remediated-customer-data"

  tags = merge(local.common_tags, {
    DataClassification = "Confidential"
    SecurityOwner      = "Cloud Security Team"
  })
}

resource "aws_s3_bucket_public_access_block" "customer_data" {
  bucket = aws_s3_bucket.customer_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "customer_data" {
  bucket = aws_s3_bucket.customer_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }

    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "customer_data" {
  bucket = aws_s3_bucket.customer_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_security_group" "secure_web" {
  name        = "cloudguard-remediated-security-group"
  description = "Security group with restricted administrative access"
  vpc_id      = "vpc-0123456789abcdef0"

  ingress {
    description = "HTTP web traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH from approved administrative network"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"

    # TEST-ONLY documentation network.
    # Replace with an approved corporate VPN CIDR in a real environment.
    cidr_blocks = ["192.0.2.0/24"]
  }

  egress {
    description = "Outbound HTTPS traffic"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "cloudguard-remediated-security-group"
  })
}

resource "aws_iam_policy" "secure_read_only_policy" {
  name        = "cloudguard-remediated-read-only-policy"
  description = "Limited read-only policy for the portfolio lab"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Sid    = "ReadOnlyCustomerData"
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket"
        ]

        Resource = [
          aws_s3_bucket.customer_data.arn,
          "${aws_s3_bucket.customer_data.arn}/*"
        ]
      }
    ]
  })

  tags = local.common_tags
}
