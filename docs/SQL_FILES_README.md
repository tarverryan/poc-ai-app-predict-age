# SQL Files for Age Prediction Pipeline

This document explains the SQL file structure and organization for the age prediction ML pipeline.

## SQL File Organization

SQL files exist in **two locations** for different purposes:

### 1. `/sql/` Directory - Reference & Standalone Execution
**Purpose:** Reference copies and standalone execution via scripts

These files are:
- Used by recovery scripts (`scripts/recover_s3_athena_resources.sh`)
- Used by utility scripts (`scripts/fix_and_execute_tables.py`)
- Reference copies for documentation
- Can be executed directly with Athena CLI

**Files:**
- `01_ai_agent_kb_predict_age_database.sql` - Creates database
- `02_ai_agent_kb_predict_age_predict_age_staging_parsed_features_2025q3.sql` - Staging table
- `03_ai_agent_kb_predict_age_predict_age_real_training_features_14m.sql` - Training features
- `04_ai_agent_kb_predict_age_predict_age_real_training_targets_14m.sql` - Training targets
- `05_ai_agent_kb_predict_age_predict_age_full_evaluation_features_378m.sql` - Evaluation features
- `tables_together.sql` - Join query for all tables
- `test_json_parsing.sql` - Test query for JSON parsing

### 2. `/lambda-predict-age/*/` Directories - Lambda Function Execution
**Purpose:** SQL files embedded in Lambda deployment packages

These files are:
- **Source of truth** for Lambda function execution
- Read directly by Lambda functions at runtime
- Packaged into Lambda deployment ZIP files
- Use `${DATABASE_NAME}`, `${S3_BUCKET}`, `${SOURCE_DATABASE}`, `${SOURCE_TABLE}` placeholders

**Locations:**
- `lambda-predict-age/ai-agent-predict-age-staging-features/staging_parsed_features.sql`
- `lambda-predict-age/ai-agent-predict-age-feature-engineering/real_training_features_14m.sql`
- `lambda-predict-age/ai-agent-predict-age-feature-engineering/real_training_targets_14m.sql`
- `lambda-predict-age/ai-agent-predict-age-feature-engineering/full_evaluation_features_378m.sql`

## Important Notes

1. **Lambda files are the source of truth** - When updating SQL, update the Lambda directory files first
2. **Keep `/sql/` in sync** - Update reference copies in `/sql/` after changing Lambda files
3. **Placeholders** - All SQL files use placeholders that are replaced at runtime:
   - `${DATABASE_NAME}` - Athena database name (default: `ml_predict_age`)
   - `${S3_BUCKET}` - S3 bucket for data storage
   - `${SOURCE_DATABASE}` - Source database name
   - `${SOURCE_TABLE}` - Source table name

## Original Documentation

The following sections describe the SQL files in detail:

## Execution Order

Run these SQL files in order to set up the pipeline:

### 1. **01_ai_agent_kb_predict_age_database.sql**
- Creates the database (configure via `${DATABASE_NAME}` placeholder, default: `ml_predict_age`)
- Sets S3 location: `s3://${S3_BUCKET}/predict-age/`
- Run once during initial setup

### 2. **02_ai_agent_kb_predict_age_predict_age_staging_parsed_features_2025q3.sql** ⭐ CRITICAL
- Parses JSON fields from source data (education, work_experience, skills)
- Creates `predict_age_staging_parsed_features_2025q3` table
- **S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_staging_parsed_features_2025q3/`
- **Size:** 378M records
- **Time:** ~15-20 minutes
- **Cost:** ~$0.50 (scans full source table)
- **Purpose:** Pre-parse JSON once to avoid repeated parsing overhead

**Parsed Fields:**
- `education_level` (1-5: high school → PhD)
- `graduation_year` (extracted from education JSON)
- `number_of_jobs` (count of work experiences)
- `skill_count` (count of skills listed)

### 3. **03_ai_agent_kb_predict_age_predict_age_real_training_features_14m.sql**
- Creates training feature table with 21 features
- Creates `predict_age_real_training_features_14m` table
- **S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_real_training_features_14m/`
- **Source:** `predict_age_staging_parsed_features_2025q3`
- **Filter:** `MOD(pid, 10) = 0` (10% sample)
- **Size:** ~14M records
- **Time:** ~3-5 minutes
- **Cost:** ~$0.02

**Features (21 total):**
1. tenure_months
2. job_level_encoded
3. job_seniority_score
4. compensation_encoded
5. company_size_encoded
6. linkedin_activity_score
7. days_since_profile_update
8. social_media_presence_score
9. email_engagement_score
10. industry_typical_age
11. job_function_encoded
12. company_revenue_encoded
13. quarter
14. education_level_encoded ⭐ NEW (from JSON)
15. graduation_year ⭐ NEW (from JSON)
16. number_of_jobs ⭐ NEW (from JSON)
17. skill_count ⭐ NEW (from JSON)
18. total_career_years ⭐ NEW (calculated)
19. job_churn_rate ⭐ NEW (calculated)
20. tenure_job_level_interaction
21. comp_size_interaction

### 4. **03_real_training_targets_14m.sql**
- Creates training target table (actual ages)
- Creates `predict_age_real_training_targets_14m` table
- **S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_real_training_targets_14m/`
- **Source:** `pid_03_foundation_with_surplus_2025q3`
- **Filter:** `MOD(pid, 10) = 0` (matches training features)
- **Age Range:** 18-75 years (outliers removed)
- **Size:** ~14M records
- **Time:** ~2-3 minutes
- **Cost:** ~$0.01

### 5. **04_full_evaluation_features_378m.sql**
- Creates evaluation feature table for ALL PIDs
- Creates `predict_age_full_evaluation_features_378m` table
- **S3 Path:** `s3://${S3_BUCKET}/predict-age/predict_age_full_evaluation_features_378m/`
- **Source:** `predict_age_staging_parsed_features_2025q3`
- **Size:** 378M records (100% coverage)
- **Batches:** 898 batches × ~420K records
- **Time:** ~12-15 minutes
- **Cost:** ~$0.05
- **Purpose:** Features for batch prediction

### 6. **05_test_json_parsing.sql** (Test Query)
- Validates JSON parsing logic
- Returns 10 sample records with parsed fields
- **Run this first** before creating staging table
- **Cost:** <$0.01

---

## Usage Examples

### Option 1: AWS CLI (Automated)
```bash
# Create database
aws athena start-query-execution \
  --query-string "$(cat sql/00_create_database.sql)" \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/ \
  --region us-east-1

# Create staging table (JSON parsing)
aws athena start-query-execution \
  --query-string "$(cat sql/01_staging_parsed_features.sql)" \
  --query-execution-context Database=ai_agent_kb_predict_age \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/ \
  --region us-east-1

# Create training features
aws athena start-query-execution \
  --query-string "$(cat sql/02_real_training_features_14m.sql)" \
  --query-execution-context Database=ai_agent_kb_predict_age \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/ \
  --region us-east-1

# Create training targets
aws athena start-query-execution \
  --query-string "$(cat sql/03_real_training_targets_14m.sql)" \
  --query-execution-context Database=ai_agent_kb_predict_age \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/ \
  --region us-east-1

# Create evaluation features
aws athena start-query-execution \
  --query-string "$(cat sql/04_full_evaluation_features_378m.sql)" \
  --query-execution-context Database=ai_agent_kb_predict_age \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/predict-age/athena-results/ \
  --region us-east-1
```

### Option 2: Athena Console (Manual)
1. Open AWS Athena Console
2. Copy/paste each SQL file content
3. Run in order (00 → 01 → 02 → 03 → 04)
4. Monitor query progress and costs

---

## Cost Breakdown

| SQL File | Scan Size | Time | Cost |
|----------|-----------|------|------|
| 00_create_database.sql | 0 GB | <1 min | $0.00 |
| 01_staging_parsed_features.sql | ~100 GB | 15-20 min | ~$0.50 |
| 02_real_training_features_14m.sql | ~10 GB | 3-5 min | ~$0.02 |
| 03_real_training_targets_14m.sql | ~5 GB | 2-3 min | ~$0.01 |
| 04_full_evaluation_features_378m.sql | ~100 GB | 12-15 min | ~$0.05 |
| **Total** | **~215 GB** | **~35-45 min** | **~$0.58** |

---

## Troubleshooting

### Issue: "Database does not exist"
**Solution:** Run `00_create_database.sql` first

### Issue: "Table staging_parsed_features_2025q3 not found"
**Solution:** Run `01_staging_parsed_features.sql` first (takes 15-20 min)

### Issue: "JSON parsing error"
**Solution:** Run `05_test_json_parsing.sql` to validate JSON structure

### Issue: "Query timeout"
**Solution:** Increase Athena query timeout or split into smaller batches

### Issue: "Permission denied writing to S3"
**Solution:** Check IAM role has `s3:PutObject` permission for `s3://${S3_BUCKET}/predict-age/`

---

## Maintenance

### Quarterly Updates
When new quarterly data arrives (e.g., 2025q4):

1. Update table suffix: `2025q3` → `2025q4`
2. Re-run `01_staging_parsed_features.sql` (new quarter source)
3. Re-run `02-04` SQL files (new training/evaluation data)
4. Re-train models with updated data

### Cleanup Old Quarters
```sql
-- Drop old staging tables
DROP TABLE IF EXISTS ai_agent_kb_predict_age.staging_parsed_features_2025q2;

-- Drop old training/evaluation tables
DROP TABLE IF EXISTS ai_agent_kb_predict_age.real_training_features_14m_2025q2;
```

---

## Key Insights

### Why Staging Table?
- **Performance:** Parse JSON once, not 898 times during prediction
- **Cost:** $0.50 once vs $0.50 × 898 = $449 without staging
- **Time:** 15 min once vs 15 min × 898 = 224 hours without staging

### Why 21 Features?
- Original plan: 15 features (without JSON parsing)
- Added 6 features from JSON data:
  - education_level_encoded
  - graduation_year
  - number_of_jobs
  - skill_count
  - total_career_years ⭐ (strongest predictor!)
  - job_churn_rate
- **Expected Improvement:** MAE 4-5 years → 3-4 years

### Why MOD(pid, 10) = 0?
- Deterministic 10% sampling
- Ensures training set is consistent across runs
- Balances speed vs accuracy (14M records sufficient)

---

**Last Updated:** October 19, 2025  
**Version:** 1.0  
**Status:** Ready for Production

