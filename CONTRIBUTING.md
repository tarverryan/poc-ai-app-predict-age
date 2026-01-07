# Contributing

This project is designed to be educational and demonstrate serverless ML pipeline patterns on AWS. It showcases architectural patterns for building scalable, cost-aware ML systems.

## Project Overview

This is a learning project that demonstrates batch ML orchestration using:
- **AWS Step Functions** for orchestration
- **AWS Fargate** for ML training and prediction
- **Amazon Athena** for data warehousing
- **Amazon S3** for data lake storage
- **Terraform** for Infrastructure as Code

## Setup Instructions

### Prerequisites

- AWS Account with appropriate permissions
- Terraform >= 1.0
- AWS CLI configured
- Docker (for building container images)
- Python 3.11+ (for local development)

### 1. Clone Repository

```bash
git clone https://github.com/tarverryan/poc-ai-app-predict-age.git
cd poc-ai-app-predict-age
```

### 2. Configure Terraform Variables

Create a `terraform/terraform.tfvars` file:

```hcl
aws_region           = "us-east-1"
project_name         = "ai-agent-predict-age"
environment          = "dev"  # Use 'dev' for learning projects
data_bucket          = "your-data-bucket-name"
source_data_bucket   = "your-source-data-bucket"  # Optional
production_data_bucket = "your-production-bucket"  # Optional
database_name        = "ml_predict_age"           # Optional, default shown
```

### 3. Configure Terraform Backend

Create a `terraform/backend.hcl` file:

```hcl
bucket         = "your-terraform-state-bucket"
key            = "predict-age/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "terraform-state-lock"
encrypt        = true
```

### 4. Initialize Terraform

```bash
cd terraform
terraform init -backend-config=backend.hcl
```

### 5. Review and Apply

```bash
terraform plan
terraform apply
```

### 6. Build and Push Docker Images

```bash
# Build training image
cd ../fargate-predict-age/ai-agent-predict-age-training
docker build -t ai-agent-predict-age-training .
docker tag ai-agent-predict-age-training:latest <ECR_REPO_URL>:latest
docker push <ECR_REPO_URL>:latest

# Build prediction image
cd ../ai-agent-predict-age-prediction
docker build -t ai-agent-predict-age-prediction .
docker tag ai-agent-predict-age-prediction:latest <ECR_REPO_URL>:latest
docker push <ECR_REPO_URL>:latest
```

### 7. Set Up Source Data

Ensure your source data is available in the configured S3 bucket and Athena database. The pipeline expects:
- Source table: Configure via `SOURCE_DATABASE` and `SOURCE_TABLE` environment variables (e.g., `source_db.source_table_2025q3`)
- Database: Configure via `DATABASE_NAME` environment variable (default: `ml_predict_age`, will be created if it doesn't exist)

**Note:** Use synthetic or anonymized data for learning purposes. Do not use real personal identifiable information.

### 8. Run Pipeline

Start the Step Functions execution:

```bash
aws stepfunctions start-execution \
  --state-machine-arn <STATE_MACHINE_ARN> \
  --name "manual-run-$(date +%Y%m%d-%H%M%S)"
```

## Project Structure

```
.
├── terraform/              # Infrastructure as Code
│   ├── main.tf            # Core infrastructure
│   ├── lambda.tf          # Lambda functions
│   ├── fargate.tf         # ECS/Fargate resources
│   └── step_functions.tf  # Step Functions state machine
├── lambda-predict-age/     # Lambda function code
├── fargate-predict-age/    # Docker containers for ML
├── sql/                    # Athena SQL queries
├── docs/                   # Comprehensive documentation
└── scripts/                # Utility scripts
```

## Environment Variables

### Required for Lambda Functions
- `S3_BUCKET` - S3 bucket for data storage
- `DATABASE_NAME` - Athena database name (default: `ml_predict_age`)
- `WORKGROUP` - Athena workgroup (default: "primary")
- `SOURCE_DATABASE` - Source database name for input data (required for staging)
- `SOURCE_TABLE` - Source table name for input data (required for staging)

### Required for Fargate Tasks
- `S3_BUCKET` - S3 bucket for data storage
- `DATABASE_NAME` - Athena database name (default: `ml_predict_age`)
- `WORKGROUP` - Athena workgroup
- `BATCH_ID` - Batch ID for prediction tasks (set by Step Functions)
- `RAW_TABLE` - Source table name for predictions

## Cost Considerations

**Important:** Actual costs vary by region, data size, and usage patterns. Always monitor your AWS billing.

Primary cost drivers:
- **Athena:** Charges per TB of data scanned – optimize with Parquet compression
- **Fargate:** CPU/memory × duration × task count
- **S3 Storage:** Data size × storage class × retention
- **Step Functions:** State transitions (minimal cost)
- **Lambda:** Invocation count × duration (minimal cost)

**Recommendations:**
- Use AWS sandbox accounts or set budget limits for learning
- Set up CloudWatch cost alarms
- Use lifecycle policies to automatically clean up old data
- Right-size Fargate tasks to match workload needs

See [docs/architecture.md](docs/architecture.md) for more details on cost optimization strategies.

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Architecture Overview](docs/architecture.md)
- [Lessons Learned](docs/lessons-learned.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [Deployment Guide](docs/deployment/DEPLOYMENT_SUMMARY.md)
- [Cost Optimization](docs/operations/COST_OPTIMIZATION_SMART_FILTERING.md)
- [Troubleshooting](docs/troubleshooting/PIPELINE_FIX_SUMMARY.md)

## Questions or Issues?

For questions or to learn more about the architecture decisions, see the [README](README.md) and documentation. This is an open-source learning project designed to help others understand serverless ML pipeline patterns on AWS.

## License

MIT License - See [LICENSE](LICENSE) for details.
