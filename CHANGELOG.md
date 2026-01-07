# Changelog

All notable changes to the AI Age Prediction Pipeline will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2025-10-23 - Recovery & Organization

### 🔄 Resource Recovery
- Recovered all S3 and Athena resources after accidental deletion
- Restored 4 base tables (Staging, Training Features, Training Targets, Evaluation Features)
- Fixed SQL issues: tenure_months CTE, date parsing with TRY_CAST, connection count parsing
- Optimized Evaluation Features query: removed ROW_NUMBER() sort, using MOD(pid, 898) hash-based batching
- Query performance: 27 seconds (was 50+ minutes)

### 📊 Cross-Table Query
- Created `tables_together.sql`: joins all 7 prediction result tables
- Features: INNER JOINs, lowercase y/n flags, all scores formatted as 0.00-100.00%
- Type casting: fixed BIGINT/VARCHAR mismatches across tables
- Decimal formatting: DECIMAL(10,2) enforces 2 decimal places (100.00 format)

### 🗂️ Project Organization
- Reorganized root directory files to docs/ and sql/
- Updated README per master.mdc rules (lightweight, no emojis, direct links)
- Moved PROJECT_STRUCTURE.md to docs/
- Moved tables.md to docs/, tables_together.sql to sql/

---

## [1.0.0] - 2025-10-23 - Production Release

### ✅ Production Deployment
- **Status:** Production-ready with 378M age predictions (100% coverage)
- **Performance:** MAE 2.23 years, R² 0.739, 83.2% high quality
- **Cost:** $15 per run, $60 annually (quarterly runs)
- **Runtime:** 45 minutes end-to-end

### 🤖 Bedrock Agent Added
- Created comprehensive Knowledge Base with 13 documents (173 KB)
- Built and tested Bedrock Agent (4 iterations)
- Final performance: 3.57/5.00 (71% accuracy across 35 test queries)
- Best category: SQL Queries (4.60/5.00)
- Agent ID: `XIGMZVBUV8`, KB ID: `WKVANDULTR`

### 📚 Documentation
- **Knowledge Base:** 13 comprehensive documents covering:
  - Model overview and performance
  - Features (all 22 detailed)
  - Confidence scoring (dual system)
  - Data schema and SQL examples
  - FAQ (40+ questions)
  - Example queries (20+ SQL samples)
  - Business guidelines
  - Troubleshooting
  - Pipeline architecture
  - Cost analysis
  - Quick start guide
  - Model validation
- **Agent Documentation:** Setup guide, test queries (168 documented), final report
- **Project Structure:** Comprehensive structure document (PROJECT_STRUCTURE.md)

### 🗂️ Project Organization
- Reorganized test files into `/tests/` directory
- Created `/tests/agent-tests/results/` for test artifacts
- Updated `.gitignore` to exclude temp files
- Cleaned up root directory (moved all test files)

### 🔍 Testing
- Automated test suite: 35 comprehensive queries
- Test coverage: 9 categories (Model Performance, Confidence, SQL, Data, Features, Cost, Architecture, Business, Troubleshooting)
- 4 iterations of agent enhancement performed
- Test results documented in JSON format

### 🏗️ Infrastructure
- All AWS resources verified and cleaned
- Athena: 5 production tables, no temp tables
- S3: Organized structure (agent-context-upload/, final-results/, models/, permanent/)
- No unnecessary resources remaining

---

## [0.9.0] - 2025-10-21 - Pipeline Fixes and Production Execution

### 🐛 Critical Bug Fixes
- **Fixed:** Removed `LIMIT 10000` clause in prediction query (was causing under-prediction)
- **Impact:** Increased prediction count from 10K/batch to full batch size (~263K/batch)
- **Result:** 236M ML predictions generated (vs 9M before fix)

### 💰 Cost Optimization
- **Smart Filtering:** Only predict for PIDs missing age data (141.7M have real data)
- **Cost Savings:** 37.5% reduction (saved ~$8 per run)
- **Implementation:** Added `WHERE (birth_year IS NULL AND approximate_age IS NULL)` filter

### 📊 Confidence Score Enhancement
- **Dual System:** Added confidence_pct (0-100%) alongside original interval width
- **Formula:** `confidence_pct = max(0, 100 - abs(original) * 3.33)`
- **New View:** Created `predict_age_final_results_with_confidence`
- **Interpretation:** 100% = real data/excellent ML, 80%+ = good for email, 60%+ = good for segments

### ✅ Production Execution
- **Completed:** Full 378M PID processing (October 21, 2025)
- **Runtime:** 32 minutes 51 seconds
- **Results:** 378,024,173 rows (100% coverage)
- **Breakdown:** 141.7M real data (37.5%), 236.3M ML predictions (62.5%)

---

## [0.8.0] - 2025-10-20 - Manual Testing and Validation

### 🧪 Manual Testing
- **8 Manual Tests Performed:**
  1. External table creation (378M dataset)
  2. Schema verification (Parquet type checking)
  3. Smart filtering validation
  4. Pre-cleanup Lambda testing
  5. Prediction Lambda testing (10K sample)
  6. Human QA Lambda testing
  7. Final Results Lambda testing
  8. Step Functions configuration validation
- **Status:** All tests PASSED

### 🔧 Fixes from Testing
- **Type Casting:** Fixed birth_year and approximate_age CAST operations
- **Schema Updates:** Changed pid from VARCHAR to BIGINT in predictions table
- **Query Optimization:** Added filters and limits for testing
- **Lambda Configuration:** Updated environment variables for 378M dataset

---

## [0.7.0] - 2025-10-19 - Initial Training and Model Evaluation

### 🤖 Model Training
- **Models Trained:** Ridge Regression, XGBoost Regressor, Quantile Forest
- **Training Data:** 14,171,296 PIDs with known ages
- **Features:** 22 employee-related features
- **Best Model:** XGBoost with MAE 2.23 years (28% better than Ridge)

### 📈 Model Performance
- **MAE:** 2.23 years (very good for age prediction)
- **R² Score:** 0.739 (explains 73.9% of age variance)
- **RMSE:** 5.05 years
- **Accuracy:** 50% within ±2 years, 75% within ±5 years, 95% within ±10 years
- **Top Feature:** total_career_years (23.4% importance)

### 🏗️ Infrastructure Deployment
- **Terraform:** Deployed all infrastructure (ECS, Lambda, Step Functions, Athena, S3)
- **Docker:** Built and pushed training and prediction containers to ECR
- **Step Functions:** 8-stage pipeline with 898 parallel Fargate tasks (max 500 concurrent)

---

## [0.6.0] - 2025-10-19 - Pipeline Design and Implementation

### 🚀 Pipeline Architecture
- **Orchestration:** AWS Step Functions (8 stages)
- **Training:** Single Fargate task (16 vCPU, 64 GB RAM)
- **Prediction:** 898 parallel Fargate tasks (4 vCPU, 16 GB RAM each)
- **Coordination:** 6 Lambda functions
- **Storage:** S3 (Parquet format, ~15 GB final results)
- **Query Engine:** AWS Athena

### 💡 Key Design Decisions
- **Inline JSON Parsing:** Parse raw JSON during prediction (eliminated separate ETL step)
- **Parquet Output:** Columnar format for efficient querying (90% storage reduction)
- **Parallel Processing:** 898 batches with max 500 concurrent for speed
- **Smart Filtering:** Predict only for PIDs missing age data (37.5% cost savings)

---

## [0.5.0] - 2025-10-18 - Data Preparation

### 📊 Data Sources
- **Training Data:** 14,171,296 PIDs with known ages (birth_year or approximate_age)
- **Evaluation Data:** 378,024,173 PIDs total (100% coverage target)
- **Existing Age Data:** 141,727,672 PIDs (37.5%) with birth_year or approximate_age
- **Need Prediction:** 236,296,501 PIDs (62.5%)

### 🗄️ Athena Tables Created
- `predict_age_training_raw_14m` - Training data (JSON)
- `predict_age_training_targets_14m` - Training targets (known ages)
- `predict_age_full_evaluation_raw_378m` - Full evaluation dataset (JSON)

---

## [0.4.0] - 2025-10-17 - Feature Engineering

### 🔧 Feature Development
- **22 Features Engineered:**
  - Career tenure (total_career_years, tenure_months, company_tenure_years)
  - Job characteristics (job_level, job_function, job_seniority_score)
  - Compensation (compensation_encoded)
  - Company attributes (company_size, company_revenue)
  - Profile richness (work_experience_count, education_level, skills_count)
  - Digital footprint (linkedin_connection_count, social_media_presence)
  - Engagement (email_engagement_score, days_since_profile_update)
  - Industry context (industry_typical_age, industry_turnover_rate)
  - Temporal (quarter)
  - Interactions (tenure_job_level_interaction, comp_size_interaction)

---

## [0.3.0] - 2025-10-16 - Requirements and Design

### 📋 Requirements Defined
- **Target:** Predict age for 378M employees/contacts
- **Output:** Integer age (18-75) + confidence score (0-1)
- **Accuracy Goal:** MAE ≤ 5 years
- **Cost Target:** < $20 per run
- **Runtime Target:** < 1 hour end-to-end

### 🎯 Model Selection
- **Primary:** XGBoost Regressor (best accuracy)
- **Baseline:** Ridge Regression (fast, interpretable)
- **Confidence:** Quantile Regression Forest (prediction intervals)

---

## [0.2.0] - 2025-10-15 - Project Setup

### 🏗️ Initial Setup
- Repository created: `ai-app-predict-age`
- Project structure defined (fargate/, lambda/, terraform/, docs/)
- README and documentation templates created
- `.gitignore` configured for Python, Terraform, AWS

---

## [0.1.0] - 2025-10-14 - Project Initialization

### 🎬 Project Start
- Project concept defined: Age prediction ML pipeline
- Reference architecture identified: `app-ai-predict-job-change`
- Technology stack selected: AWS Fargate, Step Functions, XGBoost, Athena
- Initial requirements documented

---

## Version Summary

| Version | Date | Milestone | Status |
|---------|------|-----------|--------|
| 1.0.0 | 2025-10-23 | Production Release + Bedrock Agent | ✅ Complete |
| 0.9.0 | 2025-10-21 | Pipeline Fixes + Production Execution | ✅ Complete |
| 0.8.0 | 2025-10-20 | Manual Testing | ✅ Complete |
| 0.7.0 | 2025-10-19 | Model Training + Evaluation | ✅ Complete |
| 0.6.0 | 2025-10-19 | Pipeline Implementation | ✅ Complete |
| 0.5.0 | 2025-10-18 | Data Preparation | ✅ Complete |
| 0.4.0 | 2025-10-17 | Feature Engineering | ✅ Complete |
| 0.3.0 | 2025-10-16 | Requirements + Design | ✅ Complete |
| 0.2.0 | 2025-10-15 | Project Setup | ✅ Complete |
| 0.1.0 | 2025-10-14 | Project Initialization | ✅ Complete |

---

**Current Version:** 1.0.0 - Production  
**Last Updated:** October 23, 2025  
**Repository:** https://github.com/tarverryan/poc-ai-app-predict-age
