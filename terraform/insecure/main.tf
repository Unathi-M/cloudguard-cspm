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

resource "aws_s3_bucket" "customer_data" {
  bucket = "cloudguard-demo-customer-data"

  # Intentionally missing:
  # - encryption
  # - access logging
  # - versioning
  # - tags
}

resource "aws_s3_bucket_acl" "customer_data" {
  bucket = aws_s3_bucket.customer_data.id
  acl    = "public-read"
}

resource "aws_s3_bucket_public_access_block" "customer_data" {
  bucket = aws_s3_bucket.customer_data.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_security_group" "insecure_web" {
  name        = "cloudguard-insecure-security-group"
  description = "Intentionally insecure security group"
  vpc_id      = "vpc-0123456789abcdef0"

  ingress {
    description = "SSH open to the entire internet"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP open to the entire internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_policy" "insecure_admin_policy" {
  name        = "cloudguard-insecure-admin-policy"
  description = "Intentionally over-permissive IAM policy"

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      }
    ]
  })
}
