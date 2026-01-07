terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration - configure via terraform init or backend config file
  # Example: terraform init -backend-config="bucket=your-terraform-state-bucket" -backend-config="dynamodb_table=your-state-lock-table"
  backend "s3" {
    # bucket, key, region, dynamodb_table should be configured via backend config
    # This prevents hardcoding organization-specific values
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ai-agent-predict-age"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "data_bucket" {
  description = "S3 bucket name for data storage (Athena tables, models, results)"
  type        = string
}

variable "source_data_bucket" {
  description = "S3 bucket name for source data (read-only access)"
  type        = string
  default     = ""
}

variable "production_data_bucket" {
  description = "S3 bucket name for production data (read-only access)"
  type        = string
  default     = ""
}

variable "database_name" {
  description = "Athena database name for ML pipeline tables"
  type        = string
  default     = "ml_predict_age"
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Use existing S3 Bucket for data storage
data "aws_s3_bucket" "data_bucket" {
  bucket = var.data_bucket
}

# IAM Role for Lambda functions
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for Lambda functions
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetWorkGroup",
          "athena:ListTableMetadata"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = concat(
          [
            "${data.aws_s3_bucket.data_bucket.arn}",
            "${data.aws_s3_bucket.data_bucket.arn}/*",
            "${data.aws_s3_bucket.data_bucket.arn}/athena-results/*"
          ],
          var.source_data_bucket != "" ? [
            "arn:aws:s3:::${var.source_data_bucket}",
            "arn:aws:s3:::${var.source_data_bucket}/*"
          ] : [],
          var.production_data_bucket != "" ? [
            "arn:aws:s3:::${var.production_data_bucket}",
            "arn:aws:s3:::${var.production_data_bucket}/*"
          ] : []
        )
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetPartitions",
          "glue:CreateTable",
          "glue:DeleteTable",
          "glue:UpdateTable",
          "glue:GetTables"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:ListTasks",
          "ecs:DescribeTasks",
          "ecs:StopTask"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:ListImages",
          "ecr:DescribeImages",
          "ecr:DescribeRepositories"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Groups for Lambda functions
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = toset([
    "staging-features",
    "feature-engineering",
    "human-qa",
    "cleanup",
    "precleanup",
    "batch-generator",
    "create-predictions-table",
    "final-results"
  ])
  
  name              = "/aws/lambda/${var.project_name}-${each.key}"
  retention_in_days = 14
  
  tags = local.common_tags
}

# EventBridge Rule for scheduling (optional)
resource "aws_cloudwatch_event_rule" "weekly_schedule" {
  name                = "${var.project_name}-weekly-schedule"
  description         = "Trigger age prediction pipeline weekly"
  schedule_expression = "rate(7 days)"
  
  tags = local.common_tags
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cost_alarm" {
  alarm_name          = "${var.project_name}-cost-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = "20"
  alarm_description   = "This metric monitors estimated charges"
  alarm_actions       = []

  dimensions = {
    Currency = "USD"
  }
  
  tags = local.common_tags
}

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket for data storage"
  value       = data.aws_s3_bucket.data_bucket.bucket
}

output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.weekly_schedule.arn
}

