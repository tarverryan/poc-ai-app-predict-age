# Naming Convention - Age Prediction Pipeline

**Last Updated:** October 19, 2025  
**Database:** `ai_agent_kb_predict_age`  
**S3 Base Path:** `s3://${S3_BUCKET}/predict-age/`

---

## Naming Rules

### 1. **All Tables Must Have `predict_age_` Prefix**
Every table in the `ai_agent_kb_predict_age` database starts with `predict_age_`

### 2. **S3 Path Matches Table Name Exactly**
Each table's data is stored in S3 at: `s3://${S3_BUCKET}/predict-age/{table_name}/`

### 3. **Athena Results Path is Separate**
Ad-hoc query results go to: `s3://${S3_BUCKET}/predict-age/athena-results/`  
This path is NOT used for table storage.

---

## Complete Table List

| Table Name | S3 Path | Description |
|-----------|---------|-------------|
| `predict_age_staging_parsed_features_2025q3` | `s3://${S3_BUCKET}/predict-age/predict_age_staging_parsed_features_2025q3/` | Staging table with pre-parsed JSON |
| `predict_age_real_training_features_14m` | `s3://${S3_BUCKET}/predict-age/predict_age_real_training_features_14m/` | Training features (21 cols, 14M rows) |
| `predict_age_real_training_targets_14m` | `s3://${S3_BUCKET}/predict-age/predict_age_real_training_targets_14m/` | Training targets (ages, 14M rows) |
| `predict_age_full_evaluation_features_378m` | `s3://${S3_BUCKET}/predict-age/predict_age_full_evaluation_features_378m/` | Evaluation features (21 cols, 378M rows) |
| `predict_age_predictions_2025q3` | `s3://${S3_BUCKET}/predict-age/predict_age_predictions_2025q3/` | Raw predictions (378M rows) |
| `predict_age_human_qa_2025q3` | `s3://${S3_BUCKET}/predict-age/predict_age_human_qa_2025q3/` | QA validation table |
| `predict_age_final_results_2025q3` | `s3://${S3_BUCKET}/predict-age/predict_age_final_results_2025q3/` | Production results (100% coverage) |

---

## Full Qualified Table Names (FQN)

When querying, use full database.table format:

```sql
-- Example: Query staging table
SELECT COUNT(*) 
FROM ai_agent_kb_predict_age.predict_age_staging_parsed_features_2025q3;

-- Example: Query training features
SELECT * 
FROM ai_agent_kb_predict_age.predict_age_real_training_features_14m 
LIMIT 10;

-- Example: Query final results
SELECT pid, age_prediction, age_prediction_score
FROM ai_agent_kb_predict_age.predict_age_final_results_2025q3
WHERE age_prediction_score > 0.8;
```

---

## S3 Directory Structure

```
s3://${S3_BUCKET}/predict-age/
├── predict_age_staging_parsed_features_2025q3/    (378M rows, Parquet)
├── predict_age_real_training_features_14m/        (14M rows, Parquet)
├── predict_age_real_training_targets_14m/         (14M rows, Parquet)
├── predict_age_full_evaluation_features_378m/     (378M rows, Parquet, bucketed)
├── predict_age_predictions_2025q3/                (378M rows, JSONL)
├── predict_age_human_qa_2025q3/                   (378M rows, Parquet)
├── predict_age_final_results_2025q3/              (378M rows, Parquet)
├── models/                                        (Ridge, XGBoost, QRF models)
├── evaluation/                                    (Metrics JSON)
└── athena-results/                                (Ad-hoc queries ONLY, auto-cleaned)
```

---

## Athena Query Result Location

**For all SQL executions, use this result location:**

```bash
--result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/
```

This is used for:
- ✅ CREATE TABLE query outputs
- ✅ SELECT query results  
- ✅ Test queries
- ✅ Ad-hoc analysis

**NOT used for:**
- ❌ Table data storage (uses external_location in CREATE TABLE)
- ❌ Model storage (uses `models/` directory)
- ❌ Prediction outputs (uses table-specific paths)

---

## Quarterly Suffix Pattern

Tables with quarterly data use `_YYYYqQ` suffix:

| Quarter | Suffix | Example Table |
|---------|--------|---------------|
| Q1 2025 | `_2025q1` | `predict_age_staging_parsed_features_2025q1` |
| Q2 2025 | `_2025q2` | `predict_age_staging_parsed_features_2025q2` |
| Q3 2025 | `_2025q3` | `predict_age_staging_parsed_features_2025q3` |
| Q4 2025 | `_2025q4` | `predict_age_staging_parsed_features_2025q4` |

**Tables WITH quarterly suffix:**
- `predict_age_staging_parsed_features_{yyyyqq}`
- `predict_age_predictions_{yyyyqq}`
- `predict_age_human_qa_{yyyyqq}`
- `predict_age_final_results_{yyyyqq}`

**Tables WITHOUT quarterly suffix (regenerated each run):**
- `predict_age_real_training_features_14m`
- `predict_age_real_training_targets_14m`
- `predict_age_full_evaluation_features_378m`

---

## AWS CLI Examples

### Create Database
```bash
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS ai_agent_kb_predict_age LOCATION 's3://${S3_BUCKET}/predict-age/'" \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/ \
  --region us-east-1
```

### Create Staging Table
```bash
aws athena start-query-execution \
  --query-string "$(cat sql/01_staging_parsed_features.sql)" \
  --query-execution-context Database=ai_agent_kb_predict_age \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/ \
  --region us-east-1
```

### Query Final Results
```bash
aws athena start-query-execution \
  --query-string "SELECT COUNT(*), AVG(age_prediction) FROM ai_agent_kb_predict_age.predict_age_final_results_2025q3" \
  --query-execution-context Database=ai_agent_kb_predict_age \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/ \
  --region us-east-1
```

---

## Validation Checklist

Before running the pipeline, verify naming:

- [ ] All table names start with `predict_age_`
- [ ] Each table's S3 path matches: `s3://${S3_BUCKET}/predict-age/{table_name}/`
- [ ] Athena results path is: `s3://${S3_BUCKET}/predict-age/athena-results/`
- [ ] SQL files reference correct table names with prefix
- [ ] Quarterly tables have `_2025q3` suffix
- [ ] Training/evaluation tables have no quarterly suffix

---

## Drop All Tables (Cleanup)

```sql
-- Drop all predict_age tables
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_staging_parsed_features_2025q3;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_real_training_features_14m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_real_training_targets_14m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_full_evaluation_features_378m;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_predictions_2025q3;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_human_qa_2025q3;
DROP TABLE IF EXISTS ai_agent_kb_predict_age.predict_age_final_results_2025q3;
```

---

**Summary:**
- ✅ Consistent `predict_age_` prefix on ALL tables
- ✅ S3 paths match table names exactly
- ✅ `athena-results/` reserved for ad-hoc queries only
- ✅ Clear quarterly suffix pattern for time-series tables

