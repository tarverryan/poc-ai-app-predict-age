# Age Prediction Pipeline - Technical Architecture

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Region:** us-east-1

---

## Architecture Overview

The Age Prediction Pipeline is an AWS-based, fully automated ML pipeline that trains regression models and generates age predictions for 378 million employees/contacts using parallel processing.

**Key Technologies:**
- **AWS Step Functions** - Pipeline orchestration
- **AWS Fargate** - Training and prediction containers
- **AWS Lambda** - Data preparation and aggregation
- **AWS Athena** - Data warehouse and querying
- **AWS S3** - Storage for data, models, and results
- **Terraform** - Infrastructure as Code

---

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│  378M PIDs (Raw Data in S3)                                │
│  - 37.5% have existing age (birth_year/approximate_age)    │
│  - 62.5% need ML predictions                               │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Pre-Cleanup Lambda                                │
│  - Remove old prediction files from S3                     │
│  - Clean Athena tables                                      │
│  - Prepare for new run                                      │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Training (Fargate Container)                      │
│  - Load 14M training samples with known ages               │
│  - Extract 22 features                                      │
│  - Train 3 models: Ridge, XGBoost, Quantile Forest        │
│  - Save models to S3                                        │
│  Duration: ~15 min | Cost: $0.30                           │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Batch Generator Lambda                            │
│  - Calculate batches needed (e.g., 898 for 236M PIDs)     │
│  - Generate batch IDs: [0, 1, 2, ..., 897]                │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Create Predictions Table Lambda                   │
│  - Pre-create Athena table schema                          │
│  - Define Parquet format                                    │
│  - Set S3 location                                          │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Parallel Prediction (Step Functions Map State)   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  898 Fargate Tasks (Max 500 concurrent)            │  │
│  │  Each task:                                          │  │
│  │    1. Load batch of PIDs (modulo-based filtering)   │  │
│  │    2. Apply smart filter (only PIDs missing age)    │  │
│  │    3. Parse JSON inline (extract 22 features)       │  │
│  │    4. Load models from S3                            │  │
│  │    5. Make predictions (XGBoost + confidence)       │  │
│  │    6. Save to S3 (Parquet format)                   │  │
│  └─────────────────────────────────────────────────────┘  │
│  Duration: ~25 min | Cost: $13.92                          │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 6: Human QA Lambda                                   │
│  - Join source data with predictions                       │
│  - Create 1:1 mapping for review                           │
│  - Generate QA table                                        │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 7: Final Results Lambda                              │
│  - Merge ML predictions with existing ages                 │
│  - Priority: real data > ML predictions > default          │
│  - Add confidence scores, prediction sources               │
│  - Create final table (378M rows, 100% coverage)          │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 8: Post-Cleanup Lambda                               │
│  - Remove intermediate prediction files                     │
│  - Clean up staging tables                                  │
│  - Preserve final results only                             │
└─────────────────┬───────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────┐
│  OUTPUT: predict_age_final_results_with_confidence         │
│  - 378M PIDs with age predictions                          │
│  - Dual confidence scores (original + percentage)          │
│  - Prediction source tracking                              │
│  - 100% coverage, 83% high quality (≥60% confidence)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Training Container (Fargate)

**Image:** `ai-agent-predict-age-training`  
**Resources:** 16 vCPU, 64 GB RAM  
**Duration:** ~15 minutes  
**Cost:** $0.30 per run

**Process:**
1. Load training data from Athena (14M PIDs with known ages)
2. Extract 22 features from JSON profiles
3. Train 3 models:
   - **Ridge Regression** (baseline)
   - **XGBoost** (primary predictor)
   - **Quantile Forest** (confidence intervals)
4. Evaluate models on test set
5. Save models to S3 (`s3://${S3_BUCKET}/predict-age/models/`)

**Key Features:**
- Efficient data loading (columnar Parquet when possible)
- Feature engineering (22 derived features)
- Hyperparameters (default XGBoost for now)
- Model serialization (joblib format)

---

### 2. Prediction Container (Fargate)

**Image:** `ai-agent-predict-age-prediction`  
**Resources:** 4 vCPU, 16 GB RAM per task  
**Tasks:** 898 parallel (max 500 concurrent)  
**Duration:** ~25 minutes total  
**Cost:** $13.92 per run

**Process (per task):**
1. **Load Batch Data:**
   ```sql
   SELECT * FROM raw_table
   WHERE MOD(CAST(pid AS BIGINT), 898) = {batch_id}
     AND (birth_year IS NULL AND approximate_age IS NULL)
   ```
   - Modulo-based partitioning ensures even distribution
   - Smart filter reduces unnecessary predictions by 37.5%

2. **Inline JSON Parsing:**
   - Extract 22 features on-the-fly from `profile_json` column
   - No separate parsing step (cost optimization)
   - Handle missing values with domain defaults

3. **Load Models:**
   - Download from S3 once per task
   - Cache in memory for batch processing

4. **Make Predictions:**
   - XGBoost for main prediction
   - Quantile models for confidence intervals
   - Confidence score = pred_95th - pred_5th

5. **Save Results:**
   - Output to S3 as Parquet: `batch_{batch_id}.parquet`
   - Columns: pid, predicted_age, confidence_score, model_version

**Key Features:**
- Parallel execution (898 tasks)
- Smart filtering (only predict missing ages)
- Inline parsing (eliminate separate ETL step)
- Efficient output (Parquet compression)

---

### 3. Lambda Functions

#### 3.1 Pre-Cleanup Lambda

**Runtime:** Python 3.11  
**Memory:** 512 MB  
**Duration:** ~30 seconds

**Actions:**
- Delete old S3 prediction files (`s3://*/predictions/batch_*.parquet`)
- Drop old Athena tables (if exist)
- Verify S3 paths and permissions

---

#### 3.2 Batch Generator Lambda

**Runtime:** Python 3.11  
**Memory:** 256 MB  
**Duration:** <1 second

**Logic:**
```python
total_pids_needing_prediction = 236_296_501
batch_size = 300_000  # Target rows per batch
num_batches = ceil(total_pids_needing_prediction / batch_size)  # = 898

return {"batch_ids": list(range(num_batches))}  # [0, 1, 2, ..., 897]
```

---

#### 3.3 Create Predictions Table Lambda

**Runtime:** Python 3.11  
**Memory:** 512 MB  
**Duration:** ~5 seconds

**SQL:**
```sql
CREATE EXTERNAL TABLE IF NOT EXISTS predict_age_predictions (
    pid BIGINT,
    predicted_age INT,
    confidence_score DOUBLE,
    model_version VARCHAR(50),
    prediction_timestamp TIMESTAMP
)
STORED AS PARQUET
LOCATION 's3://${S3_BUCKET}/predict-age/predictions/';
```

---

#### 3.4 Human QA Lambda

**Runtime:** Python 3.11  
**Memory:** 1024 MB  
**Duration:** ~2 minutes

**SQL:**
```sql
CREATE TABLE predict_age_human_qa AS
SELECT 
    s.pid,
    s.birth_year,
    s.approximate_age,
    pred.predicted_age,
    pred.confidence_score,
    CASE 
        WHEN s.birth_year IS NOT NULL THEN 2025 - s.birth_year
        WHEN s.approximate_age IS NOT NULL THEN s.approximate_age
        ELSE pred.predicted_age
    END as final_age
FROM source_table s
LEFT JOIN predict_age_predictions pred
    ON s.pid = pred.pid;
```

---

#### 3.5 Final Results Lambda

**Runtime:** Python 3.11  
**Memory:** 2048 MB  
**Duration:** ~2 minutes

**SQL (simplified):**
```sql
CREATE TABLE predict_age_final_results AS
SELECT 
    COALESCE(s.pid, pred.pid) as pid,
    COALESCE(
        s.approximate_age,           -- Priority 1: Real approximate age
        (2025 - s.birth_year),       -- Priority 2: Calculated from birth year
        pred.predicted_age,          -- Priority 3: ML prediction
        35                           -- Priority 4: Default fallback
    ) as predicted_age,
    CASE 
        WHEN s.birth_year IS NOT NULL OR s.approximate_age IS NOT NULL THEN 100.0
        ELSE GREATEST(0, LEAST(100, 100 - (ABS(pred.confidence_score) * 3.33)))
    END as confidence_pct,
    CASE 
        WHEN s.approximate_age IS NOT NULL OR s.birth_year IS NOT NULL THEN 'EXISTING_APPROX_AGE'
        WHEN pred.predicted_age IS NOT NULL THEN 'ML_PREDICTION'
        ELSE 'DEFAULT'
    END as prediction_source,
    CURRENT_TIMESTAMP as qa_timestamp
FROM source_table s
FULL OUTER JOIN predict_age_predictions pred
    ON s.pid = pred.pid;
```

**Key Logic:**
- Prioritize real data over ML predictions
- Assign 100% confidence to real data
- Transform ML confidence to 0-100% scale
- Track prediction source for transparency

---

#### 3.6 Post-Cleanup Lambda

**Runtime:** Python 3.11  
**Memory:** 512 MB  
**Duration:** ~1 minute

**Actions:**
- Delete intermediate prediction files (optional)
- Drop staging tables
- Preserve final results table
- Log completion metrics

---

### 4. Step Functions State Machine

**Definition:** `terraform/step_functions.tf`  
**Orchestration Type:** Standard workflow  
**Execution Time:** ~45 minutes

**States:**
1. **PreCleanup** (Task) → Lambda
2. **Training** (Task) → Fargate
3. **BatchGenerator** (Task) → Lambda
4. **CreatePredictionsTable** (Task) → Lambda
5. **ParallelPrediction** (Map) → 898 Fargate tasks
   - **MaxConcurrency:** 500
   - **ItemsPath:** $.batch_ids
   - **Iterator:** RunFargateTask
6. **HumanQA** (Task) → Lambda
7. **FinalResults** (Task) → Lambda
8. **Cleanup** (Task) → Lambda

**Error Handling:**
- Retry (3 attempts) with exponential backoff
- Catch all errors → Send SNS notification
- Failed tasks logged to CloudWatch

---

## Data Flow

### Input Data

**Source:** `ai_agent_kb_predict_age.predict_age_full_evaluation_raw_378m`  
**Format:** JSON (row format)  
**Size:** ~42 GB  
**Columns:**
- `pid` (BIGINT) - Person identifier
- `birth_year` (INT) - Year of birth (if known)
- `approximate_age` (INT) - Approximate age (if known)
- `profile_json` (STRING) - JSON object with 50+ fields

**Example:**
```json
{
  "pid": 123456789,
  "birth_year": 1985,
  "approximate_age": 40,
  "profile_json": {
    "tenure_months": 84,
    "job_level": "Senior",
    "linkedin_connections": 847,
    "education_level": "Master's",
    ...
  }
}
```

---

### Training Data

**Source:** `ai_agent_kb_predict_age.predict_age_training_raw_14m`  
**Format:** JSON (row format)  
**Size:** ~4.2 GB  
**Records:** 14,171,296 PIDs with known ages

**Usage:**
- Sample 1M for training (for speed)
- 80/20 train/test split
- All 14M used for feature engineering validation

---

### Output Data

**Table:** `predict_age_final_results_with_confidence`  
**Format:** Parquet (columnar)  
**Size:** ~15 GB  
**Records:** 378,024,173 (100% coverage)

**Schema:**
```sql
CREATE VIEW predict_age_final_results_with_confidence AS
SELECT 
    pid BIGINT,
    predicted_age INT,
    confidence_score_original DOUBLE,
    confidence_pct DOUBLE,
    prediction_source VARCHAR(50),
    qa_timestamp TIMESTAMP
FROM predict_age_final_results_2025q3;
```

---

## Infrastructure Components

### AWS Services Used

| Service | Purpose | Cost Driver |
|---------|---------|-------------|
| **Step Functions** | Orchestration | Negligible ($0.025/1000 transitions) |
| **Fargate** | Training + Prediction | Main cost ($14/run) |
| **Lambda** | Coordination | Negligible ($0.25/run) |
| **Athena** | Data queries | Moderate ($0.50/run) |
| **S3** | Storage | Low ($1.31/month) |
| **ECR** | Docker images | Low (<$0.10/month) |
| **CloudWatch** | Logs + Monitoring | Low ($0.05/run) |

---

### Terraform Modules

**Repository:** `/terraform/`

**Key Resources:**
- `step_functions.tf` - State machine definition
- `fargate.tf` - ECS cluster, task definitions
- `lambda.tf` - All 6 Lambda functions
- `iam.tf` - Execution roles and policies
- `s3.tf` - Buckets and lifecycle policies
- `athena.tf` - Database and workgroup

**Deployment:**
```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

---

## Scalability

### Current Scale
- **PIDs:** 378M (100% coverage)
- **Predictions:** 236M ML predictions
- **Batches:** 898 parallel tasks
- **Concurrency:** 500 max (limited by AWS quota)
- **Runtime:** 45 minutes

### Scaling to 1 Billion PIDs

**Estimate:**
- Predictions needed: ~625M (assuming 37.5% have real ages)
- Batches: 2,084 (at 300K per batch)
- Concurrency: 500 (same)
- Runtime: ~60 minutes (linear scaling)
- Cost: $36 per run (2.4x current)

**Bottlenecks:**
- Fargate task quota (500 concurrent tasks)
- Athena query result size (10 GB limit)

**Solutions:**
- Request AWS quota increase (500 → 1000)
- Use S3 Select for larger datasets
- Increase batch size (300K → 500K per batch)

---

## Monitoring and Observability

### CloudWatch Metrics

**Step Functions:**
- Execution duration
- State transitions
- Failed executions

**Fargate:**
- CPU utilization
- Memory utilization
- Task success/failure rate

**Lambda:**
- Invocation count
- Duration
- Errors

**Athena:**
- Query execution time
- Data scanned
- Query failures

---

### Logging

**Locations:**
- Step Functions: `/aws/states/predict-age-pipeline`
- Fargate: `/ecs/predict-age-training`, `/ecs/predict-age-prediction`
- Lambda: `/aws/lambda/predict-age-*`

**Retention:** 7 days (default)

---

### Alerts

**CloudWatch Alarms (recommended):**
- Step Functions execution failure
- Fargate task failure rate >5%
- Lambda errors >10 per hour
- Athena query cost >$10 per query

---

## Security

### IAM Roles

**Fargate Task Role:**
- `s3:GetObject` - Read models and data
- `s3:PutObject` - Write predictions
- `athena:StartQueryExecution` - Query data
- `athena:GetQueryResults` - Fetch results
- `logs:CreateLogStream`, `logs:PutLogEvents` - Logging

**Lambda Execution Role:**
- `athena:*` - Full Athena access
- `s3:*` - Full S3 access (scoped to specific buckets)
- `glue:*` - Athena table creation
- `logs:*` - CloudWatch logging

**Step Functions Execution Role:**
- `ecs:RunTask` - Launch Fargate tasks
- `lambda:InvokeFunction` - Call Lambdas
- `iam:PassRole` - Pass roles to Fargate

---

### Data Encryption

- **S3:** Server-side encryption (SSE-S3)
- **Athena:** Query results encrypted
- **Fargate:** Environment variables not used for secrets (use Secrets Manager if needed)

---

### Network

- **Fargate:** Runs in private subnets with NAT gateway
- **Lambda:** No VPC (uses AWS service endpoints)

---

## Cost Optimization

### Current Optimizations

1. **Smart Filtering** (37.5% cost reduction)
   - Only predict for PIDs missing age data
   - Saves ~$6 per run

2. **Inline JSON Parsing** (50% cost reduction)
   - Eliminate separate parsing step
   - Saves ~$14 per run

3. **Parquet Format** (90% storage reduction)
   - Columnar compression
   - Saves query costs (less data scanned)

4. **Parallel Processing** (10x speed improvement)
   - 500 concurrent tasks vs sequential
   - Reduces runtime from ~4 hours to 25 minutes

---

### Future Optimizations

1. **Spot Instances for Fargate** (70% cost reduction)
   - Use Fargate Spot for prediction tasks
   - Potential savings: ~$10 per run

2. **S3 Intelligent-Tiering** (30% storage reduction)
   - Auto-move old results to cheaper storage
   - Savings: ~$0.40/month

3. **Model Compression** (10% speed improvement)
   - Quantize models for faster loading
   - Negligible cost impact

---

## Disaster Recovery

### Backup Strategy

**Models:**
- Stored in S3 (11 9's durability)
- Versioned (can rollback)
- Cross-region replication (optional)

**Results:**
- Stored in S3 (11 9's durability)
- Athena tables point to S3 (no data loss)

**Pipeline:**
- Terraform state in S3 (versioned)
- Can rebuild infrastructure from code

---

### Recovery Procedures

**Scenario 1: Failed Execution**
- Step Functions automatically retries (3 attempts)
- If still fails, manual restart from failed step

**Scenario 2: Corrupted Results**
- Rollback to previous quarter's results
- Re-run pipeline (45 minutes)

**Scenario 3: Infrastructure Deletion**
- Terraform rebuild (10 minutes)
- Re-run pipeline (45 minutes)

---

## Future Enhancements

### Q1 2026
- REST API endpoint (Lambda + API Gateway)
- Real-time prediction (Lambda inference)
- Automated quarterly runs (EventBridge scheduler)

### Q2 2026
- Model A/B testing framework
- Ensemble models (XGBoost + LightGBM)
- Feature drift monitoring

---

## Technical Specifications

**Code Languages:** Python 3.11, SQL (Athena), HCL (Terraform)  
**Docker Base Image:** python:3.11-slim  
**ML Libraries:** scikit-learn, xgboost, pandas, numpy  
**AWS SDK:** boto3  
**Infrastructure:** 100% Terraform

---

**For Operational Details:** See `10-cost-and-performance.md`  
**For Troubleshooting:** See `08-troubleshooting.md`
