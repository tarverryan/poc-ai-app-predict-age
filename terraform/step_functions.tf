# IAM Role for Step Functions
resource "aws_iam_role" "step_functions_role" {
  name = "${var.project_name}-step-functions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      },
    ]
  })

  tags = local.common_tags
}

# IAM Policy for Step Functions
resource "aws_iam_role_policy" "step_functions_policy" {
  name = "${var.project_name}-step-functions-policy"
  role = aws_iam_role.step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction",
        ]
        Resource = [
          aws_lambda_function.staging_features.arn,
          aws_lambda_function.feature_engineering.arn,
          aws_lambda_function.human_qa.arn,
          aws_lambda_function.cleanup.arn,
          aws_lambda_function.precleanup.arn,
          aws_lambda_function.batch_generator.arn,
          aws_lambda_function.create_predictions_table.arn,
          aws_lambda_function.final_results.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask",
          "ecs:StopTask",
          "ecs:DescribeTasks",
        ]
        Resource = [
          aws_ecs_task_definition.training.arn,
          aws_ecs_task_definition.prediction.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole",
        ]
        Resource = [
          aws_iam_role.fargate_task_role.arn,
          aws_iam_role.fargate_execution_role.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeClusters",
        ]
        Resource = [
          aws_ecs_cluster.main.arn
        ]
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
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:ListBucketMultipartUploads",
          "s3:ListMultipartUploadParts",
          "s3:AbortMultipartUpload",
          "s3:PutObject"
        ]
        Resource = concat(
          [
            "arn:aws:s3:::${data.aws_s3_bucket.data_bucket.bucket}",
            "arn:aws:s3:::${data.aws_s3_bucket.data_bucket.bucket}/*"
          ],
          var.source_data_bucket != "" ? [
            "arn:aws:s3:::${var.source_data_bucket}",
            "arn:aws:s3:::${var.source_data_bucket}/*"
          ] : []
        )
      },
      {
        Effect = "Allow"
        Action = [
          "glue:CreateDatabase",
          "glue:DeleteDatabase",
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:UpdateDatabase",
          "glue:CreateTable",
          "glue:DeleteTable",
          "glue:BatchDeleteTable",
          "glue:UpdateTable",
          "glue:GetTable",
          "glue:GetTables",
          "glue:BatchCreatePartition",
          "glue:CreatePartition",
          "glue:DeletePartition",
          "glue:BatchDeletePartition",
          "glue:UpdatePartition",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutRule",
          "events:DeleteRule",
          "events:PutTargets",
          "events:RemoveTargets",
          "events:DescribeRule"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/stepfunctions/${var.project_name}-pipeline"
  retention_in_days = 14

  tags = local.common_tags
}

# Step Functions State Machine
resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.project_name}-pipeline"
  role_arn = aws_iam_role.step_functions_role.arn
  type     = "STANDARD"

  definition = jsonencode({
    Comment = "ML Pipeline: Pre-Cleanup -> Staging Features -> Training Features -> Training -> Evaluation Features -> Prediction -> Human QA -> Final Results -> Cleanup"
    StartAt = "PreCleanup"
    States = {
      PreCleanup = {
        Type     = "Task"
        Resource = aws_lambda_function.precleanup.arn
        Comment  = "Pre-cleanup: Drop final results table and clean S3 to prevent duplicates on re-run"
        Next     = "StagingFeatures"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      StagingFeatures = {
        Type     = "Task"
        Resource = aws_lambda_function.staging_features.arn
        Comment  = "Create staging table with pre-parsed JSON features (15-20 min, $0.50)"
        Next     = "TrainingFeatures"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      TrainingFeatures = {
        Type     = "Task"
        Resource = aws_lambda_function.feature_engineering.arn
        Parameters = {
          mode = "training"
        }
        Next     = "Training"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 6
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      Training = {
        Type       = "Task"
        Resource   = "arn:aws:states:::ecs:runTask.sync"
        Parameters = {
          Cluster              = aws_ecs_cluster.main.arn
          TaskDefinition       = aws_ecs_task_definition.training.arn
          LaunchType           = "FARGATE"
          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = data.aws_subnets.default.ids
              SecurityGroups = [aws_security_group.fargate_tasks.id]
              AssignPublicIp = "ENABLED"
            }
          }
          Overrides = {
            ExecutionRoleArn = aws_iam_role.fargate_execution_role.arn
            TaskRoleArn      = aws_iam_role.fargate_task_role.arn
          }
        }
        TimeoutSeconds = 2400  # 40 minutes timeout
        Next           = "EvaluationFeatures"
        Retry = [
          {
            ErrorEquals     = ["States.ALL"]
            IntervalSeconds = 30
            MaxAttempts     = 3
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      EvaluationFeatures = {
        Type     = "Task"
        Resource = aws_lambda_function.feature_engineering.arn
        Parameters = {
          mode = "full_evaluation"
        }
        ResultPath = "$.evaluationFeaturesResult"
        Next       = "GenerateBatchIds"
        Comment    = "Create evaluation features for all 378M PIDs (12-15 min)"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 30
            MaxAttempts     = 3
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      GenerateBatchIds = {
        Type     = "Task"
        Resource = aws_lambda_function.batch_generator.arn
        Comment  = "Generate 898 batch IDs for parallel prediction (~420K records each)"
        Next     = "CreatePredictionsTable"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 6
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      CreatePredictionsTable = {
        Type     = "Task"
        Resource = aws_lambda_function.create_predictions_table.arn
        Comment  = "Pre-create predictions table ONCE before parallel tasks (eliminates race condition)"
        ResultPath = "$.tableCreationResult"
        Next     = "ParallelPrediction"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      ParallelPrediction = {
        Type = "Map"
        Comment = "Run prediction in parallel for all batches (898 batches of ~420K records each)"
        ItemsPath = "$.batch_ids"
        MaxConcurrency = 500  # MAXIMUM SPEED: 500 parallel tasks (~10 min for 378M predictions!)
        ResultPath = null  # Don't collect results - prevents 256KB output limit error
        Parameters = {
          "batch_id.$" = "$$.Map.Item.Value"
        }
        Iterator = {
          StartAt = "RunPredictionBatch"
          States = {
            RunPredictionBatch = {
              Type = "Task"
              Resource = "arn:aws:states:::ecs:runTask.sync"
              Parameters = {
                Cluster = aws_ecs_cluster.main.arn
                TaskDefinition = aws_ecs_task_definition.prediction.arn
                LaunchType = "FARGATE"
                NetworkConfiguration = {
                  AwsvpcConfiguration = {
                    Subnets = data.aws_subnets.default.ids
                    SecurityGroups = [aws_security_group.fargate_tasks.id]
                    AssignPublicIp = "ENABLED"
                  }
                }
                Overrides = {
                  ExecutionRoleArn = aws_iam_role.fargate_execution_role.arn
                  TaskRoleArn = aws_iam_role.fargate_task_role.arn
                  ContainerOverrides = [
                    {
                      Name = "prediction"
                      Environment = [
                        {
                          Name = "BATCH_ID"
                          "Value.$" = "States.Format('{}', $.batch_id)"
                        },
                        {
                          Name = "RAW_TABLE"
                          Value = "predict_age_full_evaluation_raw_378m"  # Production: 378M PIDs
                        },
                        {
                          Name = "TOTAL_BATCHES"
                          Value = "898"
                        }
                      ]
                    }
                  ]
                }
              }
              TimeoutSeconds = 3600  # 1 hour per batch
              End = true
              Retry = [
                {
                  ErrorEquals = ["States.ALL"]
                  IntervalSeconds = 30
                  MaxAttempts = 3
                  BackoffRate = 2
                }
              ]
            }
          }
        }
        Next = "HumanQA"
        Retry = [
          {
            ErrorEquals     = ["States.ALL"]
            IntervalSeconds = 30
            MaxAttempts     = 3
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      HumanQA = {
        Type     = "Task"
        Resource = aws_lambda_function.human_qa.arn
        Next     = "FinalResults"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 6
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      FinalResults = {
        Type     = "Task"
        Resource = aws_lambda_function.final_results.arn
        Comment  = "Create final results table with 1:1 mapping to source (378M PIDs). Includes default predictions (Age: 35, Confidence: 15.0) for PIDs with missing data."
        Next     = "WaitForFinalResults"
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 6
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "PipelineFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      WaitForFinalResults = {
        Type    = "Wait"
        Seconds = 180
        Comment = "Wait 3 minutes for final results table to complete (378M records)"
        Next    = "Cleanup"
      }
      Cleanup = {
        Type     = "Task"
        Resource = aws_lambda_function.cleanup.arn
        Comment  = "Comprehensive cleanup: Drop intermediate tables, clean S3, verify no active resources. KEEPS ONLY final results table and data."
        End      = true
        Retry = [
          {
            ErrorEquals     = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2
          }
        ]
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "CleanupFailed"
            ResultPath  = "$.error"
          }
        ]
      }
      CleanupFailed = {
        Type  = "Fail"
        Cause = "Cleanup failed - manual intervention may be required to remove intermediate resources"
      }
      PipelineFailed = {
        Type  = "Fail"
        Cause = "Pipeline execution failed"
      }
    }
  })

  tags = local.common_tags
}

# Outputs
output "step_functions_state_machine_arn" {
  description = "ARN of the Step Functions State Machine"
  value       = aws_sfn_state_machine.pipeline.arn
}

output "step_functions_state_machine_name" {
  description = "Name of the Step Functions State Machine"
  value       = aws_sfn_state_machine.pipeline.name
}

