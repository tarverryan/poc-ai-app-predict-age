# Project Structure

**Project:** AI Age Prediction Pipeline  
**Last Updated:** January 2025  
**Version:** 1.0 (Learning Project)

---

## 📁 Repository Structure

```
ai-app-predict-age/
├── README.md                          # Main project documentation
├── CHANGELOG.md                       # Version history and releases
├── LICENSE                            # Project license
├── PROJECT_STRUCTURE.md              # This file
│
├── docs/                              # 📚 Documentation
│   ├── README.md                      # Documentation index
│   ├── app_ai_predict_age_requirements.md        # Original requirements
│   ├── app_ai_predict_age_requirements_prompt.md # Cursor AI instructions
│   │
│   ├── architecture/                  # Architecture documentation
│   │   └── CONFIDENCE_SCALE_GUIDE.md  # Confidence scoring system
│   │
│   ├── bedrock-agent/                 # 🤖 Bedrock Agent setup
│   │   ├── kb-source/                 # Knowledge Base documents (13 files)
│   │   │   ├── 00-knowledge-base-manifest.md
│   │   │   ├── 01-model-overview.md
│   │   │   ├── 02-features.md
│   │   │   ├── 03-interpreting-confidence.md
│   │   │   ├── 04-data-schema.md
│   │   │   ├── 05-faq.md
│   │   │   ├── 06-example-queries.md
│   │   │   ├── 07-business-guidelines.md
│   │   │   ├── 08-troubleshooting.md
│   │   │   ├── 09-pipeline-architecture.md
│   │   │   ├── 10-cost-and-performance.md
│   │   │   ├── 11-quick-start.md
│   │   │   └── 12-model-performance.md
│   │   ├── AGENT_SETUP_COMPLETE.md    # Agent setup guide
│   │   ├── AGENT_TEST_QUERIES.md      # 168 test queries
│   │   └── AGENT_FINAL_REPORT.md      # Performance assessment
│   │
│   ├── deployment/                    # Deployment guides
│   │   └── DEPLOYMENT_SUMMARY.md
│   │
│   ├── operations/                    # Operational docs
│   │   ├── COST_OPTIMIZATION_SMART_FILTERING.md
│   │   └── NEXT_STEPS.md
│   │
│   ├── reports/                       # Execution reports
│   │   └── PRODUCTION_EXECUTION_SUMMARY.md
│   │
│   ├── testing/                       # Test documentation
│   │   ├── LAMBDA_TEST_RESULTS.md
│   │   ├── MANUAL_TESTING_REPORT.md
│   │   └── VALIDATION_REPORT.md
│   │
│   └── troubleshooting/               # Troubleshooting guides
│       └── PIPELINE_FIX_SUMMARY.md
│
├── fargate-predict-age/               # 🐋 Docker containers
│   ├── ai-agent-predict-age-training/ # Training container
│   │   ├── Dockerfile
│   │   ├── training.py               # Model training script
│   │   └── requirements.txt
│   └── ai-agent-predict-age-prediction/ # Prediction container
│       ├── Dockerfile
│       ├── prediction.py             # Prediction script (inline JSON parsing)
│       └── requirements.txt
│
├── lambda-predict-age/                # λ Lambda Functions
│   ├── ai-agent-predict-age-pre-cleanup/
│   │   └── lambda_function.py        # Pre-execution cleanup
│   ├── ai-agent-predict-age-batch-generator/
│   │   └── lambda_function.py        # Generate batch IDs for parallel processing
│   ├── ai-agent-predict-age-create-predictions-table/
│   │   └── lambda_function.py        # Create Athena predictions table
│   ├── ai-agent-predict-age-human-qa/
│   │   └── lambda_function.py        # Create QA aggregation table
│   ├── ai-agent-predict-age-final-results/
│   │   └── lambda_function.py        # Merge predictions with real data
│   └── ai-agent-predict-age-cleanup/
│       └── lambda_function.py        # Post-execution cleanup
│
├── terraform/                         # 🏗️ Infrastructure as Code
│   ├── main.tf                       # Main Terraform config
│   ├── fargate.tf                    # ECS cluster, task definitions
│   ├── lambda.tf                     # Lambda function definitions
│   ├── step_functions.tf             # Step Functions state machine
│   ├── iam.tf                        # IAM roles and policies
│   ├── s3.tf                         # S3 buckets
│   ├── athena.tf                     # Athena database and workgroup
│   └── variables.tf                  # Terraform variables
│
├── tests/                             # 🧪 Testing
│   └── test_bedrock_agent.py         # Bedrock Agent test suite (35 queries)
│
└── sql/                               # 📝 SQL Scripts (Reference Copies)
    ├── 01_ai_agent_kb_predict_age_database.sql
    ├── 02_ai_agent_kb_predict_age_predict_age_staging_parsed_features_2025q3.sql
    ├── 03_ai_agent_kb_predict_age_predict_age_real_training_features_14m.sql
    ├── 04_ai_agent_kb_predict_age_predict_age_real_training_targets_14m.sql
    ├── 05_ai_agent_kb_predict_age_predict_age_full_evaluation_features_378m.sql
    ├── tables_together.sql
    └── test_json_parsing.sql
    Note: Lambda functions use SQL files in their own directories (source of truth)
```

---

## 🗂️ Key Directories

### `/docs/` - Documentation
Comprehensive project documentation organized by category:
- **architecture/** - Design decisions (confidence scoring)
- **bedrock-agent/** - AI Agent Knowledge Base (13 documents)
- **deployment/** - Deployment guides
- **operations/** - Cost optimization, next steps
- **reports/** - Production execution summaries
- **testing/** - Test results and validation
- **troubleshooting/** - Bug fixes and resolutions

### `/fargate-predict-age/` - Docker Containers
Two containerized applications:
1. **Training** - Trains Ridge, XGBoost, and Quantile Forest models on 14M samples
2. **Prediction** - Performs inline JSON parsing and predicts ages for 236M PIDs

### `/lambda-predict-age/` - Lambda Functions
6 Lambda functions orchestrating the pipeline:
1. Pre-cleanup - Removes old data
2. Batch generator - Creates 898 batch IDs
3. Create predictions table - Sets up Athena schema
4. Human QA - Joins source with predictions for review
5. Final results - Merges ML predictions with real data
6. Cleanup - Removes intermediate artifacts

### `/terraform/` - Infrastructure
Complete infrastructure definition:
- ECS cluster with Fargate capacity provider
- Step Functions state machine (8 stages)
- 6 Lambda functions with IAM roles
- Athena database and workgroup
- S3 buckets with lifecycle policies

### `/tests/` - Testing
Automated testing for Bedrock Agent:
- **test_bedrock_agent.py** - 35-query test suite
- **agent-tests/results/** - Test result artifacts

---

## 🗄️ AWS Infrastructure

### Athena Tables
**Database:** `ai_agent_kb_predict_age`

| Table | Rows | Purpose | Status |
|-------|------|---------|--------|
| `predict_age_final_results_with_confidence` | Large dataset | Final results view (dual confidence) | ✅ Active |
| `predict_age_final_results_2025q3` | Large dataset | Results table (Q3 2025) | ✅ Active |
| `predict_age_full_evaluation_raw_378m` | 378M | Source data (raw JSON) | ✅ Active |
| `predict_age_training_raw_14m` | 14M | Training data | ✅ Active |
| `predict_age_training_targets_14m` | 14M | Training targets (known ages) | ✅ Active |

### S3 Structure
**Bucket:** `s3://${S3_BUCKET}/predict-age/`

```
predict-age/
├── agent-context-upload/          # Bedrock KB documents (13 files, 173 KB)
├── final-results/                 # Final predictions (Parquet format)
├── models/                        # Trained models (3 files, 50 MB)
├── permanent/                     # Long-term storage
└── predict_age_real_training_targets_14m/  # Training targets
```

### Bedrock Resources
**Knowledge Base:**
- ID: `WKVANDULTR`
- Documents: 13 (all indexed)
- Embedding: Titan v2 (1024 dimensions)
- Status: Active

**Agent:**
- ID: `XIGMZVBUV8`
- Model: Claude 3 Sonnet
- Performance: 3.57/5.00 (71% accuracy)
- Status: Production-ready

---

## 📊 Data Flow

```
                    ┌─────────────────────────┐
                    │  Raw Data (378M PIDs)   │
                    │  S3: JSON format        │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Step Functions Start   │
                    │  (8-stage pipeline)     │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐   ┌─────────▼────────┐   ┌─────────▼────────┐
│  Pre-Cleanup   │   │  Training        │   │  Batch Generator │
│  (Lambda)      │   │  (Fargate)       │   │  (Lambda)        │
│  Remove old    │   │  14M samples     │   │  898 batches     │
└────────────────┘   │  3 models        │   └──────────────────┘
                     │  MAE 2.23        │
                     └──────────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Parallel Prediction    │
                    │  898 Fargate tasks      │
                    │  Max 500 concurrent     │
                    │  236M ML predictions    │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Human QA (Lambda)      │
                    │  Join source + preds    │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Final Results (Lambda) │
                    │  Merge: Real + ML       │
                    │  378M rows, 100% cov    │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Final Results Table    │
                    │  predict_age_final_     │
                    │  results_with_confidence│
                    └─────────────────────────┘
```

---

## 🚀 Key Files

### Configuration
- `terraform/main.tf` - Main infrastructure config
- `terraform/step_functions.tf` - Pipeline orchestration (8 stages, 898 parallel tasks)

### Core Logic
- `fargate-predict-age/ai-agent-predict-age-training/training.py` - Model training (Ridge, XGBoost, Quantile)
- `fargate-predict-age/ai-agent-predict-age-prediction/prediction.py` - Prediction with inline JSON parsing
- `lambda-predict-age/ai-agent-predict-age-final-results/lambda_function.py` - Smart filtering and data merging

### Documentation
- `README.md` - Main project overview
- `docs/bedrock-agent/kb-source/` - 13 comprehensive KB documents
- `docs/bedrock-agent/AGENT_FINAL_REPORT.md` - Agent performance (71% accuracy)

### Testing
- `tests/test_bedrock_agent.py` - Automated test suite (35 queries)
- `docs/bedrock-agent/AGENT_TEST_QUERIES.md` - All 168 test queries documented

---

## 📈 Metrics

### Data
- **Total PIDs:** 378,024,173 (378M)
- **Real Data:** 141.7M (37.5%)
- **ML Predictions:** 236.3M (62.5%)
- **High Quality (≥60% conf):** 314.4M (83.2%)

### Model Performance
- **MAE:** 2.23 years
- **R² Score:** 0.739
- **RMSE:** 5.05 years
- **Top Feature:** total_career_years (23.4% importance)

### Pipeline Performance
- **Runtime:** 45 minutes (15 training + 25 prediction + 5 coordination)
- **Cost:** $15 per run ($60 annually for quarterly runs)
- **Parallel Tasks:** 898 Fargate tasks, max 500 concurrent
- **Throughput:** 1M predictions/second (aggregate)

### Bedrock Agent
- **Performance:** 3.57/5.00 (71% accuracy)
- **Best Category:** SQL Queries (4.60/5.00)
- **Test Coverage:** 35 queries across 9 categories
- **KB Documents:** 13 (173 KB total, all indexed)

---

## 🔄 Recent Updates

**October 23, 2025:**
- ✅ Created and tested Bedrock Agent (4 iterations)
- ✅ Built Knowledge Base with 13 comprehensive documents
- ✅ Organized project structure (moved tests to `/tests/`)
- ✅ Documented agent performance (71% accuracy)
- ✅ Cleaned up temp files and verified S3/Athena

**October 21, 2025:**
- ✅ Pipeline execution complete (large-scale batch processing)
- ✅ Pipeline fix: Removed LIMIT 10000 bug
- ✅ Smart filtering implementation (37.5% cost savings)
- ✅ Confidence score transformation (dual system)

**October 19-20, 2025:**
- ✅ Initial deployment and testing
- ✅ Infrastructure setup with Terraform
- ✅ Training and prediction containers built

---

## 📚 Documentation Index

### Getting Started
- `README.md` - Quick start guide
- `docs/README.md` - Documentation index
- `docs/bedrock-agent/kb-source/11-quick-start.md` - 5-minute guide

### Architecture
- `docs/architecture/CONFIDENCE_SCALE_GUIDE.md` - Dual confidence scoring
- `docs/bedrock-agent/kb-source/09-pipeline-architecture.md` - Technical architecture

### Operations
- `docs/operations/COST_OPTIMIZATION_SMART_FILTERING.md` - Cost savings (37.5%)
- `docs/operations/NEXT_STEPS.md` - Recommended actions
- `docs/bedrock-agent/kb-source/10-cost-and-performance.md` - Detailed cost analysis

### Testing
- `docs/testing/MANUAL_TESTING_REPORT.md` - 8 manual tests
- `docs/testing/VALIDATION_REPORT.md` - Validation results
- `docs/bedrock-agent/AGENT_FINAL_REPORT.md` - Agent testing (4 iterations)

### Troubleshooting
- `docs/troubleshooting/PIPELINE_FIX_SUMMARY.md` - Critical bug fixes
- `docs/bedrock-agent/kb-source/08-troubleshooting.md` - Error resolution guide

---

## 🛠️ Development

### Building Docker Images
```bash
cd fargate-predict-age/ai-agent-predict-age-training
docker build -t predict-age-training .

cd ../ai-agent-predict-age-prediction
docker build -t predict-age-prediction .
```

### Deploying Infrastructure
```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

### Running Tests
```bash
cd tests/
python3 test_bedrock_agent.py  # Bedrock Agent test suite
```

---

## 📞 Support

**Repository:** https://github.com/tarverryan/poc-ai-app-predict-age  
**Documentation:** `/docs/`  
**Agent KB:** `/docs/bedrock-agent/kb-source/`  
**Issues:** GitHub Issues

---

**Status:** ✅ Learning Project / Reference Implementation  
**Last Updated:** October 23, 2025  
**Version:** 1.0

