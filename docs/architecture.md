# System Architecture

**Purpose:** This document describes the architecture of a learning project demonstrating batch ML orchestration patterns on AWS. This is a reference implementation for educational purposes, not a production system.

## System Purpose and Constraints

This project demonstrates how to build a serverless ML pipeline for batch processing using AWS services. The pipeline orchestrates data staging, feature engineering, model training, and parallel batch prediction.

**Key Constraints:**
- Serverless-first approach (no managed infrastructure)
- Cost-aware design (optimize for pay-per-use services)
- Scalable to handle large batch workloads
- Infrastructure as Code (Terraform)
- Learning-focused (not production-hardened)

## Component Responsibilities

### AWS Step Functions
**Role:** Central orchestrator for the entire pipeline
- Coordinates all pipeline stages
- Handles retries and error handling
- Manages parallel execution via Map state
- Provides execution history and monitoring

### AWS Lambda Functions
**Role:** Event-driven functions for orchestration and data preparation
- **Pre-cleanup:** Removes old data before pipeline run
- **Staging:** Parses JSON and creates staging tables via Athena
- **Feature Engineering:** Uses Athena CTAS to create feature sets
- **Batch Generation:** Calculates and generates batch IDs
- **Table Creation:** Pre-creates Athena tables for results
- **Aggregation:** Merges predictions with source data
- **Cleanup:** Removes intermediate data after completion

### AWS Fargate (ECS Tasks)
**Role:** Serverless containers for compute-intensive ML workloads
- **Training Container:** Trains regression models on labeled data
- **Prediction Container:** Performs batch predictions in parallel
- **Feature Parser:** One-time JSON parsing (optional optimization)

### Amazon Athena
**Role:** Serverless SQL queries on S3 data
- Feature engineering via CTAS (Create Table As Select)
- Querying staging and training data
- Creating result tables
- No infrastructure to manage, pay per query

### Amazon S3
**Role:** Data lake storage
- Source data storage
- Feature storage (Parquet format)
- Model storage (serialized models)
- Result storage (final predictions)
- Lifecycle policies for cost management

### AWS Glue Data Catalog
**Role:** Metadata catalog for Athena
- Table schema definitions
- Automatic schema discovery from Parquet
- Partition management
- External table locations

### Amazon ECR
**Role:** Container registry
- Stores Docker images for Fargate tasks
- Image versioning and scanning
- Lifecycle policies for old images

### Amazon ECS
**Role:** Container orchestration
- Manages Fargate cluster
- Task scheduling and resource allocation
- Cluster configuration

### AWS IAM
**Role:** Access control
- Least-privilege policies for all services
- Service roles for Lambda, Fargate, Step Functions
- Cross-service permissions

### Amazon CloudWatch
**Role:** Observability
- Log groups for Lambda and Fargate
- Cost alarms
- Execution history for Step Functions

### AWS VPC Endpoints
**Role:** Private connectivity
- ECR endpoint for image pulls
- S3 endpoint for data access
- CloudWatch Logs endpoint for logging
- Avoids internet gateway costs

## Data Flow

```
Source Data (S3)
    ↓
Staging Lambda → Athena CTAS → Staging Table (S3 Parquet)
    ↓
Feature Engineering Lambda → Athena CTAS → Training Features (S3 Parquet)
    ↓
Training Fargate → Load Features → Train Models → Save to S3
    ↓
Batch Generator Lambda → Generate Batch IDs
    ↓
Step Functions Map State → Launch Parallel Fargate Tasks
    ↓
Each Fargate Task → Load Batch → Predict → Save to S3 (Parquet)
    ↓
Aggregation Lambda → Merge Predictions → Final Results Table (S3 Parquet)
    ↓
Cleanup Lambda → Remove Intermediate Data
```

## Failure Handling

### Retry Strategies
- **Lambda Functions:** Automatic retries with exponential backoff (3 attempts)
- **Fargate Tasks:** Step Functions retries failed tasks (3-6 attempts depending on stage)
- **Athena Queries:** Lambda handles query failures and retries

### Error Handling
- **Step Functions Catch Blocks:** Catch errors and route to failure state
- **Lambda Error Handling:** Try-catch blocks with detailed error logging
- **Fargate Error Handling:** Exit codes and CloudWatch logs for debugging

### Idempotency
- **Pre-cleanup:** Ensures clean state before each run
- **Table Creation:** Uses `IF NOT EXISTS` to handle re-runs
- **S3 Writes:** Overwrites existing files (idempotent)

## Observability

### CloudWatch Logs
- **Lambda Log Groups:** One per function, 14-day retention
- **Fargate Log Groups:** One per container type, 7-14 day retention
- **Log Format:** Structured JSON with timestamps and context

### CloudWatch Metrics
- **Step Functions:** Execution metrics (duration, success/failure)
- **Lambda:** Invocation count, duration, errors
- **Fargate:** Task count, CPU/memory utilization
- **Athena:** Query execution metrics

### Cost Monitoring
- **CloudWatch Cost Alarms:** Alert when spending exceeds threshold
- **Cost Allocation Tags:** All resources tagged for cost tracking
- **Billing Dashboard:** Monitor service-level costs

## Cost Drivers

### Primary Cost Components
1. **Athena Data Scanned:** Largest cost driver – optimize with Parquet compression and partitioning
2. **Fargate Compute:** CPU/memory × duration × task count
3. **S3 Storage:** Data size × storage class × retention period
4. **Step Functions:** State transitions (minimal cost)
5. **Lambda:** Invocation count × duration (minimal cost)

### Cost Optimization Strategies
- **Parquet Compression:** Reduces Athena scan costs significantly
- **Right-sizing:** Match Fargate CPU/memory to workload needs
- **Lifecycle Policies:** Automatically transition/delete old data
- **Automated Cleanup:** Remove intermediate data after pipeline completion
- **VPC Endpoints:** Avoid data transfer costs

### Cost Levers
- **Data Size:** Smaller datasets = lower costs
- **Query Optimization:** Reduce Athena data scanned
- **Parallelism:** Balance speed vs cost (more tasks = higher cost)
- **Storage Retention:** Shorter retention = lower storage costs

## Security Boundaries

### IAM Least Privilege
- **Lambda Roles:** Only permissions needed for specific function
- **Fargate Task Role:** Read S3, write results, query Athena
- **Fargate Execution Role:** Pull images from ECR, write logs
- **Step Functions Role:** Invoke Lambda, run Fargate tasks, manage state

### Network Security
- **VPC Endpoints:** Private connectivity to AWS services
- **No Internet Gateway:** Fargate tasks don't need internet access
- **Security Groups:** Restrictive rules (only necessary ports)

### Data Security
- **Encryption at Rest:** S3 server-side encryption enabled
- **Encryption in Transit:** TLS for all AWS API calls
- **No Hardcoded Secrets:** All credentials via environment variables or Secrets Manager
- **Access Control:** IAM policies control who can access what

### Security Assumptions
- **AWS Account Security:** Assumes AWS account has proper security controls
- **Credential Management:** Assumes AWS credentials are properly secured
- **Data Privacy:** Assumes source data is properly anonymized or synthetic
- **Compliance:** This is guidance for learning projects, not audited compliance

## Limitations and Considerations

### Not Production-Ready
- No disaster recovery plan
- No multi-region deployment
- Limited monitoring and alerting
- No automated testing in CI/CD
- No compliance certifications

### Learning Project Scope
- Focuses on architectural patterns, not production hardening
- Demonstrates concepts, not enterprise-grade solutions
- Cost estimates are illustrative, not guaranteed
- Performance metrics are from test runs, not production workloads

---

**Last Updated:** January 2025  
**Author:** Ryan Tarver

