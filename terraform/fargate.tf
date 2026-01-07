# ECS Cluster for Fargate tasks
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

# ECR Repository for Training Docker Image
resource "aws_ecr_repository" "training" {
  name                 = "${var.project_name}-training"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# ECR Repository for Prediction Docker Image
resource "aws_ecr_repository" "prediction" {
  name                 = "${var.project_name}-prediction"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# ECR Repository for Feature Parser Docker Image (one-time use)
resource "aws_ecr_repository" "feature_parser" {
  name                 = "${var.project_name}-feature-parser"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Purpose = "One-time JSON parsing for permanent training features"
  })
}

# IAM Role for Fargate Tasks
resource "aws_iam_role" "fargate_task_role" {
  name = "${var.project_name}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      },
    ]
  })

  tags = local.common_tags
}

# IAM Policy for Fargate Tasks
resource "aws_iam_role_policy" "fargate_task_policy" {
  name = "${var.project_name}-task-policy"
  role = aws_iam_role.fargate_task_role.id

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
          "s3:GetBucketLocation",
        ]
        Resource = concat(
          [
            "arn:aws:s3:::${data.aws_s3_bucket.data_bucket.bucket}",
            "arn:aws:s3:::${data.aws_s3_bucket.data_bucket.bucket}/*",
            "arn:aws:s3:::${data.aws_s3_bucket.data_bucket.bucket}/athena-results/*"
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
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
    ]
  })
}

# IAM Role for Fargate Task Execution
resource "aws_iam_role" "fargate_execution_role" {
  name = "${var.project_name}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      },
    ]
  })

  tags = local.common_tags
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "fargate_execution_role_policy" {
  role       = aws_iam_role.fargate_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Fargate Task Definition for Training
resource "aws_ecs_task_definition" "training" {
  family                   = "ai-agent-predict-age-training"
  cpu                      = "8192"  # 8 vCPU (better availability)
  memory                   = "32768" # 32 GB
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.fargate_execution_role.arn
  task_role_arn            = aws_iam_role.fargate_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"  # Better capacity availability
  }

  container_definitions = jsonencode([
    {
      name        = "training"
      image       = "${aws_ecr_repository.training.repository_url}:latest"
      cpu         = 8192
      memory      = 32768
      essential   = true
      environment = [
        { name = "S3_BUCKET", value = data.aws_s3_bucket.data_bucket.bucket },
        { name = "DATABASE_NAME", value = var.database_name },
        { name = "WORKGROUP", value = "primary" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-training"
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.common_tags
}

# Fargate Task Definition for Prediction
resource "aws_ecs_task_definition" "prediction" {
  family                   = "ai-agent-predict-age-prediction"
  cpu                      = "4096"  # 4 vCPU (sufficient for batch prediction)
  memory                   = "16384" # 16 GB
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.fargate_execution_role.arn
  task_role_arn            = aws_iam_role.fargate_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"  # Better capacity availability
  }

  container_definitions = jsonencode([
    {
      name        = "prediction"
      image       = "${aws_ecr_repository.prediction.repository_url}:latest"
      cpu         = 4096
      memory      = 16384
      essential   = true
      environment = [
        { name = "S3_BUCKET", value = data.aws_s3_bucket.data_bucket.bucket },
        { name = "DATABASE_NAME", value = var.database_name },
        { name = "WORKGROUP", value = "primary" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-prediction"
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.common_tags
}

# Fargate Task Definition for Feature Parser (one-time use)
resource "aws_ecs_task_definition" "feature_parser" {
  family                   = "ai-agent-predict-age-feature-parser"
  cpu                      = "16384" # 16 vCPU for large dataset processing
  memory                   = "65536" # 64 GB (handles 14.17M rows in memory)
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.fargate_execution_role.arn
  task_role_arn            = aws_iam_role.fargate_task_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name        = "feature-parser"
      image       = "${aws_ecr_repository.feature_parser.repository_url}:latest"
      cpu         = 16384
      memory      = 65536
      essential   = true
      environment = [
        { name = "S3_BUCKET", value = data.aws_s3_bucket.data_bucket.bucket },
        { name = "DATABASE_NAME", value = var.database_name },
        { name = "WORKGROUP", value = "ai-agent-predict-age" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-feature-parser"
          "awslogs-region"        = data.aws_region.current.name
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, {
    Purpose = "One-time JSON parsing for permanent training features"
  })
}

# CloudWatch Log Group for Training
resource "aws_cloudwatch_log_group" "fargate_training" {
  name              = "/ecs/${var.project_name}-training"
  retention_in_days = 14

  tags = local.common_tags
}

# CloudWatch Log Group for Prediction
resource "aws_cloudwatch_log_group" "fargate_prediction" {
  name              = "/ecs/${var.project_name}-prediction"
  retention_in_days = 14

  tags = local.common_tags
}

# CloudWatch Log Group for Feature Parser
resource "aws_cloudwatch_log_group" "fargate_feature_parser" {
  name              = "/ecs/${var.project_name}-feature-parser"
  retention_in_days = 7  # Short retention for one-time use

  tags = merge(local.common_tags, {
    Purpose = "One-time JSON parsing logs"
  })
}

# Security Group for Fargate Tasks
resource "aws_security_group" "fargate_tasks" {
  name_prefix = "${var.project_name}-fargate-tasks-"
  description = "Allow outbound traffic for Fargate tasks"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-fargate-tasks"
  })
}

# Data sources for VPC configuration
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Outputs
output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecr_training_repository_url" {
  description = "URL of the ECR repository for training Docker images"
  value       = aws_ecr_repository.training.repository_url
}

output "ecr_prediction_repository_url" {
  description = "URL of the ECR repository for prediction Docker images"
  value       = aws_ecr_repository.prediction.repository_url
}

output "fargate_task_role_arn" {
  description = "ARN of the Fargate task IAM role"
  value       = aws_iam_role.fargate_task_role.arn
}

