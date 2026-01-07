# Athena Tables and S3 Paths Reference

**Project:** Age Prediction ML Pipeline  
**Database:** `ai_agent_kb_predict_age`  
**Workgroup:** `primary` (always use this)  
**Athena Results Path:** `s3://${S3_BUCKET}/athena-results/` (global, for all ad-hoc queries)  
**Date:** October 19, 2025

---

## Database

**Name:** `ai_agent_kb_predict_age`  
**S3 Location:** `s3://${S3_BUCKET}/predict-age/`  
**SQL File:** `sql/ai_agent_kb_predict_age_database.sql`

---

## All Tables (7 Total)

### 1. Staging Table (JSON Pre-Parsing)

**Table Name:** `ai_agent_kb_predict_age.predict_age_staging_parsed_features_2025q3`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_staging_parsed_features_2025q3/`  
**SQL File:** `sql/ai_agent_kb_predict_age_predict_age_staging_parsed_features_2025q3.sql`  
**Rows:** ~378M  
**Format:** Parquet (Snappy)  
**Purpose:** Pre-parse JSON fields (education, work_experience, skills) once for performance

---

### 2. Training Features

**Table Name:** `ai_agent_kb_predict_age.predict_age_real_training_features_14m`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_real_training_features_14m/`  
**SQL File:** `sql/ai_agent_kb_predict_age_predict_age_real_training_features_14m.sql`  
**Rows:** ~14M (10% sample)  
**Format:** Parquet (Snappy)  
**Purpose:** 21 features for model training

---

### 3. Training Targets

**Table Name:** `ai_agent_kb_predict_age.predict_age_real_training_targets_14m`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_real_training_targets_14m/`  
**SQL File:** `sql/ai_agent_kb_predict_age_predict_age_real_training_targets_14m.sql`  
**Rows:** ~14M (matches training features)  
**Format:** Parquet (Snappy)  
**Purpose:** Actual ages (18-75 years) for training

---

### 4. Evaluation Features (Full Dataset)

**Table Name:** `ai_agent_kb_predict_age.predict_age_full_evaluation_features_378m`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_full_evaluation_features_378m/`  
**SQL File:** `sql/ai_agent_kb_predict_age_predict_age_full_evaluation_features_378m.sql`  
**Rows:** ~378M (100% of PIDs)  
**Format:** Parquet (Snappy, bucketed)  
**Purpose:** Features for batch prediction (898 batches)

---

### 5. Predictions Table (Runtime - Created by Lambda)

**Table Name:** `ai_agent_kb_predict_age.predict_age_predictions_2025q3`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_predictions_2025q3/`  
**Created By:** Lambda function `ai-agent-predict-age-create-predictions-table`  
**Rows:** ~378M (populated by Fargate)  
**Format:** JSONL  
**Purpose:** Raw prediction outputs from model

---

### 6. Human QA Table (Created by Lambda)

**Table Name:** `ai_agent_kb_predict_age.predict_age_human_qa_2025q3`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_human_qa_2025q3/`  
**Created By:** Lambda function `ai-agent-predict-age-human-qa`  
**Rows:** ~378M  
**Format:** Parquet (Snappy)  
**Purpose:** QA validation - join all PIDs with predictions

---

### 7. Final Results Table (Created by Lambda)

**Table Name:** `ai_agent_kb_predict_age.predict_age_final_results_2025q3`  
**S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_final_results_2025q3/`  
**Created By:** Lambda function `ai-agent-predict-age-final-results`  
**Rows:** 378M (100% coverage guaranteed)  
**Format:** Parquet (Snappy)  
**Purpose:** Production-ready results with default values for missing predictions

---

## Quick Reference Table

| # | Table Name | S3 Path | SQL File | Rows |
|---|-----------|---------|----------|------|
| 1 | `predict_age_staging_parsed_features_2025q3` | `s3://${S3_BUCKET}/predict-age/predict_age_staging_parsed_features_2025q3/` | `ai_agent_kb_predict_age_predict_age_staging_parsed_features_2025q3.sql` | 378M |
| 2 | `predict_age_real_training_features_14m` | `s3://${S3_BUCKET}/predict-age/predict_age_real_training_features_14m/` | `ai_agent_kb_predict_age_predict_age_real_training_features_14m.sql` | 14M |
| 3 | `predict_age_real_training_targets_14m` | `s3://${S3_BUCKET}/predict-age/predict_age_real_training_targets_14m/` | `ai_agent_kb_predict_age_predict_age_real_training_targets_14m.sql` | 14M |
| 4 | `predict_age_full_evaluation_features_378m` | `s3://${S3_BUCKET}/predict-age/predict_age_full_evaluation_features_378m/` | `ai_agent_kb_predict_age_predict_age_full_evaluation_features_378m.sql` | 378M |
| 5 | `predict_age_predictions_2025q3` | `s3://${S3_BUCKET}/predict-age/predict_age_predictions_2025q3/` | Created by Lambda | 378M |
| 6 | `predict_age_human_qa_2025q3` | `s3://${S3_BUCKET}/predict-age/predict_age_human_qa_2025q3/` | Created by Lambda | 378M |
| 7 | `predict_age_final_results_2025q3` | `s3://${S3_BUCKET}/predict-age/predict_age_final_results_2025q3/` | Created by Lambda | 378M |

---

## S3 Directory Structure

```
s3://${S3_BUCKET}/
├── athena-results/                                          ⭐ GLOBAL (all ad-hoc queries)
│   └── {query-execution-id}.txt/csv/metadata
│
└── predict-age/
    ├── predict_age_staging_parsed_features_2025q3/          (Table 1 data)
    ├── predict_age_real_training_features_14m/              (Table 2 data)
    ├── predict_age_real_training_targets_14m/               (Table 3 data)
    ├── predict_age_full_evaluation_features_378m/           (Table 4 data)
    ├── predict_age_predictions_2025q3/                      (Table 5 data)
    ├── predict_age_human_qa_2025q3/                         (Table 6 data)
    ├── predict_age_final_results_2025q3/                    (Table 7 data)
    └── models/                                              (ML model files)
        ├── ridge_age_model.joblib
        ├── xgboost_age_model.joblib
        └── qrf_age_model.joblib
```

---

## Athena Query Configuration

### Always Use These Settings

**Workgroup:** `primary`  
**Result Location:** `s3://${S3_BUCKET}/athena-results/`  
**Region:** `us-east-1`

### AWS CLI Example

```bash
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM ai_agent_kb_predict_age.predict_age_final_results_2025q3" \
  --query-execution-context Database=ai_agent_kb_predict_age \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
  --work-group primary \
  --region us-east-1
```

---

## SQL File Naming Convention

**Pattern:** `{database_name}_{table_name}.sql`

**Example:** 
- Database: `ai_agent_kb_predict_age`
- Table: `predict_age_staging_parsed_features_2025q3`
- File: `ai_agent_kb_predict_age_predict_age_staging_parsed_features_2025q3.sql`

---

## Execution Order

Run SQL files in this order:

1. **Create Database**
   ```bash
   aws athena start-query-execution \
     --query-string "$(cat sql/ai_agent_kb_predict_age_database.sql)" \
     --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
     --work-group primary \
     --region us-east-1
   ```

2. **Create Staging Table** (15-20 min, $0.50)
   ```bash
   aws athena start-query-execution \
     --query-string "$(cat sql/ai_agent_kb_predict_age_predict_age_staging_parsed_features_2025q3.sql)" \
     --query-execution-context Database=ai_agent_kb_predict_age \
     --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
     --work-group primary \
     --region us-east-1
   ```

3. **Create Training Features** (3-5 min, $0.02)
   ```bash
   aws athena start-query-execution \
     --query-string "$(cat sql/ai_agent_kb_predict_age_predict_age_real_training_features_14m.sql)" \
     --query-execution-context Database=ai_agent_kb_predict_age \
     --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
     --work-group primary \
     --region us-east-1
   ```

4. **Create Training Targets** (2-3 min, $0.01)
   ```bash
   aws athena start-query-execution \
     --query-string "$(cat sql/ai_agent_kb_predict_age_predict_age_real_training_targets_14m.sql)" \
     --query-execution-context Database=ai_agent_kb_predict_age \
     --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
     --work-group primary \
     --region us-east-1
   ```

5. **Create Evaluation Features** (12-15 min, $0.05)
   ```bash
   aws athena start-query-execution \
     --query-string "$(cat sql/ai_agent_kb_predict_age_predict_age_full_evaluation_features_378m.sql)" \
     --query-execution-context Database=ai_agent_kb_predict_age \
     --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
     --work-group primary \
     --region us-east-1
   ```

---

## Full Qualified Table Names (FQN)

Use these in all SQL queries:

```sql
ai_agent_kb_predict_age.predict_age_staging_parsed_features_2025q3
ai_agent_kb_predict_age.predict_age_real_training_features_14m
ai_agent_kb_predict_age.predict_age_real_training_targets_14m
ai_agent_kb_predict_age.predict_age_full_evaluation_features_378m
ai_agent_kb_predict_age.predict_age_predictions_2025q3
ai_agent_kb_predict_age.predict_age_human_qa_2025q3
ai_agent_kb_predict_age.predict_age_final_results_2025q3
```

---

## Cleanup Commands

### Drop All Tables

```sql
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_staging_parsed_features_2025q3;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_real_training_features_14m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_real_training_targets_14m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_full_evaluation_features_378m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_predictions_2025q3;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_human_qa_2025q3;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_final_results_2025q3;
```

### Delete All S3 Data

```bash
aws s3 rm s3://${S3_BUCKET}/predict-age/ --recursive
```

---

**Summary:**
✅ All table names have `predict_age_` prefix  
✅ S3 paths match table names exactly  
✅ Athena results go to global path: `s3://${S3_BUCKET}/athena-results/`  
✅ Always use `primary` workgroup  
✅ SQL files named: `{db}_{table}.sql`

