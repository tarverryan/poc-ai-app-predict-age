# Lambda function for staging features (Zip)
resource "aws_lambda_function" "staging_features" {
  filename         = "../lambda-predict-age/ai-agent-predict-age-staging-features/deployment.zip"
  function_name    = "ai-agent-predict-age-staging-features"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.staging_features_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 900  # 15 minutes for staging table creation
  memory_size     = 2048
  architectures   = ["arm64"]

  environment {
    variables = {
      S3_BUCKET     = data.aws_s3_bucket.data_bucket.bucket
      DATABASE_NAME = var.database_name
      WORKGROUP     = "primary"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs["staging-features"]
  ]

  tags = local.common_tags
}

data "archive_file" "staging_features_zip" {
  type        = "zip"
  source_dir  = "../lambda-predict-age/ai-agent-predict-age-staging-features"
  output_path = "../lambda-predict-age/ai-agent-predict-age-staging-features/deployment.zip"
  excludes    = ["deployment.zip", "__pycache__", "*.pyc"]
}

# Lambda function for feature engineering (Zip)
resource "aws_lambda_function" "feature_engineering" {
  filename         = "../lambda-predict-age/ai-agent-predict-age-feature-engineering/deployment.zip"
  function_name    = "ai-agent-predict-age-feature-engineering"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.feature_engineering_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 900  # 15 minutes for full evaluation features
  memory_size     = 2048
  architectures   = ["arm64"]

  environment {
    variables = {
      S3_BUCKET     = data.aws_s3_bucket.data_bucket.bucket
      DATABASE_NAME = var.database_name
      WORKGROUP     = "primary"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs["feature-engineering"]
  ]

  tags = local.common_tags
}

data "archive_file" "feature_engineering_zip" {
  type        = "zip"
  source_dir  = "../lambda-predict-age/ai-agent-predict-age-feature-engineering"
  output_path = "../lambda-predict-age/ai-agent-predict-age-feature-engineering/deployment.zip"
  excludes    = ["deployment.zip", "__pycache__", "*.pyc"]
}

# Lambda function for pre-cleanup (Zip)
resource "aws_lambda_function" "precleanup" {
  filename         = "../lambda-predict-age/ai-agent-predict-age-precleanup/deployment.zip"
  function_name    = "ai-agent-predict-age-precleanup"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.precleanup_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 300  # 5 minutes
  memory_size     = 1024
  architectures   = ["arm64"]

  environment {
    variables = {
      S3_BUCKET     = data.aws_s3_bucket.data_bucket.bucket
      DATABASE_NAME = var.database_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs["precleanup"]
  ]

  tags = local.common_tags
}

data "archive_file" "precleanup_zip" {
  type        = "zip"
  source_dir  = "../lambda-predict-age/ai-agent-predict-age-precleanup"
  output_path = "../lambda-predict-age/ai-agent-predict-age-precleanup/deployment.zip"
  excludes    = ["deployment.zip", "__pycache__", "*.pyc"]
}

# Lambda function for batch generator (Zip)
resource "aws_lambda_function" "batch_generator" {
  filename         = "../lambda-predict-age/ai-agent-predict-age-batch-generator/deployment.zip"
  function_name    = "ai-agent-predict-age-batch-generator"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.batch_generator_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256
  architectures   = ["arm64"]

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs["batch-generator"]
  ]

  tags = local.common_tags
}

data "archive_file" "batch_generator_zip" {
  type        = "zip"
  source_dir  = "../lambda-predict-age/ai-agent-predict-age-batch-generator"
  output_path = "../lambda-predict-age/ai-agent-predict-age-batch-generator/deployment.zip"
  excludes    = ["deployment.zip", "__pycache__", "*.pyc"]
}

# Lambda function to pre-create predictions table (Zip)
resource "aws_lambda_function" "create_predictions_table" {
  filename         = "../lambda-predict-age/ai-agent-predict-age-create-predictions-table/deployment.zip"
  function_name    = "ai-agent-predict-age-create-predictions-table"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.create_predictions_table_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 60  # Quick operation (~3 seconds)
  memory_size     = 512
  architectures   = ["arm64"]

  environment {
    variables = {
      S3_BUCKET     = data.aws_s3_bucket.data_bucket.bucket
      DATABASE_NAME = var.database_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs["create-predictions-table"]
  ]

  tags = local.common_tags
}

data "archive_file" "create_predictions_table_zip" {
  type        = "zip"
  source_dir  = "../lambda-predict-age/ai-agent-predict-age-create-predictions-table"
  output_path = "../lambda-predict-age/ai-agent-predict-age-create-predictions-table/deployment.zip"
  excludes    = ["deployment.zip", "__pycache__", "*.pyc"]
}

# Lambda function for human QA (Zip)
resource "aws_lambda_function" "human_qa" {
  filename         = "../lambda-predict-age/ai-agent-predict-age-human-qa/deployment.zip"
  function_name    = "ai-agent-predict-age-human-qa"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.human_qa_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 300
  memory_size     = 1536
  architectures   = ["arm64"]

  environment {
    variables = {
      S3_BUCKET     = data.aws_s3_bucket.data_bucket.bucket
      DATABASE_NAME = var.database_name
      WORKGROUP     = "primary"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs["human-qa"]
  ]

  tags = local.common_tags
}

data "archive_file" "human_qa_zip" {
  type        = "zip"
  source_dir  = "../lambda-predict-age/ai-agent-predict-age-human-qa"
  output_path = "../lambda-predict-age/ai-agent-predict-age-human-qa/deployment.zip"
  excludes    = ["deployment.zip", "__pycache__", "*.pyc"]
}

# Lambda function for final results (Zip)
resource "aws_lambda_function" "final_results" {
  filename         = "../lambda-predict-age/ai-agent-predict-age-final-results/deployment.zip"
  function_name    = "ai-agent-predict-age-final-results"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.final_results_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 900  # 15 minutes for 378M records
  memory_size     = 2048
  architectures   = ["arm64"]

  environment {
    variables = {
      S3_BUCKET     = data.aws_s3_bucket.data_bucket.bucket
      DATABASE_NAME = var.database_name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs["final-results"]
  ]

  tags = local.common_tags
}

data "archive_file" "final_results_zip" {
  type        = "zip"
  source_dir  = "../lambda-predict-age/ai-agent-predict-age-final-results"
  output_path = "../lambda-predict-age/ai-agent-predict-age-final-results/deployment.zip"
  excludes    = ["deployment.zip", "__pycache__", "*.pyc"]
}

# Lambda function for cleanup (Zip)
resource "aws_lambda_function" "cleanup" {
  filename         = "../lambda-predict-age/ai-agent-predict-age-cleanup/deployment.zip"
  function_name    = "ai-agent-predict-age-cleanup"
  role            = aws_iam_role.lambda_execution_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.cleanup_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 900  # 15 minutes for cleanup
  memory_size     = 1024
  architectures   = ["arm64"]

  environment {
    variables = {
      DATABASE_NAME = var.database_name
      S3_BUCKET     = data.aws_s3_bucket.data_bucket.bucket
      CLUSTER_NAME  = aws_ecs_cluster.main.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs["cleanup"]
  ]

  tags = local.common_tags
}

data "archive_file" "cleanup_zip" {
  type        = "zip"
  source_dir  = "../lambda-predict-age/ai-agent-predict-age-cleanup"
  output_path = "../lambda-predict-age/ai-agent-predict-age-cleanup/deployment.zip"
  excludes    = ["deployment.zip", "__pycache__", "*.pyc"]
}

# Outputs
output "staging_features_lambda_arn" {
  description = "ARN of the staging features Lambda function"
  value       = aws_lambda_function.staging_features.arn
}

output "feature_engineering_lambda_arn" {
  description = "ARN of the feature engineering Lambda function"
  value       = aws_lambda_function.feature_engineering.arn
}

output "precleanup_lambda_arn" {
  description = "ARN of the pre-cleanup Lambda function"
  value       = aws_lambda_function.precleanup.arn
}

output "cleanup_lambda_arn" {
  description = "ARN of the cleanup Lambda function"
  value       = aws_lambda_function.cleanup.arn
}

output "human_qa_lambda_arn" {
  description = "ARN of the Human QA Lambda function"
  value       = aws_lambda_function.human_qa.arn
}

output "final_results_lambda_arn" {
  description = "ARN of the final results Lambda function"
  value       = aws_lambda_function.final_results.arn
}

