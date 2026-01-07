# Athena Database & Tables Reference

**Project:** Age Prediction ML Pipeline  
**Date:** October 19, 2025  
**Region:** us-east-1

---

## Database

**Database Name:** `ai_agent_kb_predict_age`  
**Database Location:** `s3://${S3_BUCKET}/predict-age/`  
**Athena Results Path:** `s3://${S3_BUCKET}/predict-age/athena-results/`

---

## Tables (In Creation Order)

### 1. Staging Table (JSON Pre-Parsing)

**Table Name:** `ai_agent_kb_predict_age.staging_parsed_features_2025q3`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/staging/parsed_features_2025q3/`  
**Format:** Parquet (Snappy compression)  
**Row Count:** ~378M records  
**Purpose:** Pre-parse JSON fields (education, work_experience, skills) once for performance  
**Columns:** 
- pid (bigint)
- All original fields (job_title, job_level, etc.)
- education_level (int) - parsed
- graduation_year (int) - parsed
- number_of_jobs (int) - parsed
- skill_count (int) - parsed
- education_raw, work_experience_raw, skills_raw (string) - for debugging

**Created by:** `sql/01_staging_parsed_features.sql`  
**Cost:** ~$0.50  
**Time:** 15-20 minutes

---

### 2. Training Features

**Table Name:** `ai_agent_kb_predict_age.real_training_features_14m`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/features/real_training_features_14m/`  
**Format:** Parquet (Snappy compression)  
**Row Count:** ~14M records (10% sample via MOD(pid, 10) = 0)  
**Purpose:** 21 features for model training  
**Columns:**
- pid (bigint)
- 21 feature columns (tenure_months, job_level_encoded, education_level_encoded, etc.)
- feature_creation_date (date)
- feature_version (varchar)

**Created by:** `sql/02_real_training_features_14m.sql`  
**Cost:** ~$0.02  
**Time:** 3-5 minutes

---

### 3. Training Targets

**Table Name:** `ai_agent_kb_predict_age.real_training_targets_14m`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/targets/real_training_targets_14m/`  
**Format:** Parquet (Snappy compression)  
**Row Count:** ~14M records (matches training features)  
**Purpose:** Actual ages for model training  
**Columns:**
- pid (bigint)
- actual_age (int) - target variable (18-75 years)
- birth_year (string)
- approximate_age (string)
- target_creation_date (date)
- target_version (varchar)

**Created by:** `sql/03_real_training_targets_14m.sql`  
**Cost:** ~$0.01  
**Time:** 2-3 minutes

---

### 4. Evaluation Features (Full Dataset)

**Table Name:** `ai_agent_kb_predict_age.full_evaluation_features_378m`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/features/full_evaluation_features_378m/`  
**Format:** Parquet (Snappy compression)  
**Bucketing:** 898 buckets by batch_id  
**Row Count:** ~378M records (100% of PIDs)  
**Purpose:** Features for batch prediction across all PIDs  
**Columns:**
- pid (bigint)
- batch_id (bigint) - for parallel processing (0-897)
- 21 feature columns (same as training features)
- feature_creation_date (date)
- feature_version (varchar)

**Created by:** `sql/04_full_evaluation_features_378m.sql`  
**Cost:** ~$0.05  
**Time:** 12-15 minutes

---

### 5. Predictions Table (Runtime)

**Table Name:** `ai_agent_kb_predict_age.predict_age_predictions_2025q3`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/predictions/`  
**Format:** JSONL (line-delimited JSON)  
**Row Count:** ~378M records (populated by Fargate prediction tasks)  
**Purpose:** Raw prediction outputs from model  
**Columns:**
- pid (bigint)
- age_prediction (int) - predicted age (18-75)
- age_prediction_score (double) - confidence score (0-1)
- prediction_ts (timestamp)
- model_version (varchar)
- age_prediction_lower (int) - optional 5th percentile
- age_prediction_upper (int) - optional 95th percentile

**Created by:** Lambda function `ai-agent-predict-age-create-predictions-table`  
**Populated by:** Fargate tasks (898 parallel batches)  
**Cost:** ~$10.80 (Fargate compute)  
**Time:** 10-15 minutes

---

### 6. Human QA Table

**Table Name:** `ai_agent_kb_predict_age.predict_age_human_qa_2025q3`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/human-qa/predict_age_human_qa_2025q3/`  
**Format:** Parquet (Snappy compression)  
**Row Count:** ~378M records  
**Purpose:** Quality assurance - join all PIDs with predictions to identify gaps  
**Columns:**
- pid (bigint)
- age_prediction (int) - NULL if prediction missing
- age_prediction_score (double)
- prediction_ts (timestamp)
- has_prediction (boolean) - derived flag
- known_age (int) - actual age if available (for validation)

**Created by:** Lambda function `ai-agent-predict-age-human-qa`  
**Cost:** ~$0.05  
**Time:** 2-3 minutes

---

### 7. Final Results Table

**Table Name:** `ai_agent_kb_predict_age.predict_age_final_results_2025q3`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/final-results/predict_age_final_results_2025q3/`  
**Format:** Parquet (Snappy compression)  
**Row Count:** 378M records (100% coverage guaranteed)  
**Purpose:** Production-ready results with 100% PID coverage  
**Columns:**
- pid (bigint)
- age_prediction (int) - guaranteed non-NULL (defaults to median age 34)
- age_prediction_score (double) - confidence score (0-1)
- prediction_ts (timestamp)
- model_version (varchar)
- is_default_prediction (boolean) - TRUE if median age used

**Created by:** Lambda function `ai-agent-predict-age-final-results`  
**Cost:** ~$0.05  
**Time:** 2-3 minutes

---

## Table Summary

| # | Table Name | S3 Path | Rows | Format | Purpose |
|---|-----------|---------|------|--------|---------|
| 1 | `staging_parsed_features_2025q3` | `staging/parsed_features_2025q3/` | 378M | Parquet | JSON pre-parsing ⭐ |
| 2 | `real_training_features_14m` | `features/real_training_features_14m/` | 14M | Parquet | Training features (21) |
| 3 | `real_training_targets_14m` | `targets/real_training_targets_14m/` | 14M | Parquet | Training targets (ages) |
| 4 | `full_evaluation_features_378m` | `features/full_evaluation_features_378m/` | 378M | Parquet | Evaluation features |
| 5 | `predict_age_predictions_2025q3` | `predictions/` | 378M | JSONL | Raw predictions |
| 6 | `predict_age_human_qa_2025q3` | `human-qa/predict_age_human_qa_2025q3/` | 378M | Parquet | QA validation |
| 7 | `predict_age_final_results_2025q3` | `final-results/predict_age_final_results_2025q3/` | 378M | Parquet | Production results ✅ |

**Total S3 Storage:** ~300-400 GB (Parquet compressed)

---

## Additional S3 Paths

### Model Storage
**Path:** `s3://${S3_BUCKET}/predict-age/models/`  
**Files:**
- `ridge_age_model.joblib` (~1MB)
- `xgboost_age_model.joblib` (~450MB)
- `qrf_age_model.joblib` (~1.2GB)

### Evaluation Metrics
**Path:** `s3://${S3_BUCKET}/predict-age/evaluation/`  
**Files:**
- `evaluation_metrics.json` (validation results for all 3 models)

### Athena Query Results
**Path:** `s3://${S3_BUCKET}/predict-age/athena-results/`  
**Purpose:** Default location for all Athena query outputs

---

## Cleanup Strategy

### Tables to Keep (Permanent)
- ✅ `staging_parsed_features_2025q3` - reusable for multiple runs
- ✅ `predict_age_final_results_2025q3` - production output
- ✅ `predict_age_human_qa_2025q3` - audit trail

### Tables to Drop After Pipeline (Temporary)
- ❌ `real_training_features_14m` - can be regenerated from staging
- ❌ `real_training_targets_14m` - can be regenerated from source
- ❌ `full_evaluation_features_378m` - can be regenerated from staging
- ❌ `predict_age_predictions_2025q3` - intermediate results

**Cleanup SQL:**
```sql
-- Drop temporary tables after successful pipeline run
DROP TABLE IF EXISTS ai_agent_kb_predict_age.real_training_features_14m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.real_training_targets_14m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.full_evaluation_features_378m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_predictions_2025q3;
```

---

## Quarterly Updates

When new data arrives (e.g., 2025q4), update table suffixes:

| Current (2025q3) | Next (2025q4) |
|-----------------|---------------|
| `staging_parsed_features_2025q3` | `staging_parsed_features_2025q4` |
| `predict_age_predictions_2025q3` | `predict_age_predictions_2025q4` |
| `predict_age_human_qa_2025q3` | `predict_age_human_qa_2025q4` |
| `predict_age_final_results_2025q3` | `predict_age_final_results_2025q4` |

Training/evaluation tables remain unsuffixed (regenerated each run).

---

## S3 Bucket Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::${S3_BUCKET}/predict-age/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${S3_BUCKET}"
      ],
      "Condition": {
        "StringLike": {
          "s3:prefix": [
            "predict-age/*"
          ]
        }
      }
    }
  ]
}
```

---

## Athena Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution"
      ],
      "Resource": [
        "arn:aws:athena:us-east-1:*:workgroup/primary"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:GetDatabase",
        "glue:GetTable",
        "glue:GetPartitions",
        "glue:CreateTable",
        "glue:UpdateTable",
        "glue:DeleteTable"
      ],
      "Resource": [
        "arn:aws:glue:us-east-1:*:catalog",
        "arn:aws:glue:us-east-1:*:database/ai_agent_kb_predict_age",
        "arn:aws:glue:us-east-1:*:table/ai_agent_kb_predict_age/*"
      ]
    }
  ]
}
```

---

**Last Updated:** October 19, 2025  
**Version:** 1.0  
**Status:** Ready for Creation

