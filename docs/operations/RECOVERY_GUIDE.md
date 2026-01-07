# Recovery Guide: Restore S3 and Athena Resources

**Date:** October 23, 2025  
**Status:** Recovery script ready  
**Last Updated:** 2025

---

## 🚨 Situation

All S3 resources for the age prediction pipeline were accidentally deleted. This guide provides step-by-step recovery instructions.

---

## 📊 Current State Assessment

### ✅ What Still Exists
- **Database:** Configure via `DATABASE_NAME` environment variable (default: `ml_predict_age`)
- **Source Table:** Configure via `SOURCE_DATABASE` and `SOURCE_TABLE` environment variables (e.g., `source_db.source_table_2025q3`)
- **5 Athena Tables:** (metadata exists, but S3 data is gone)
  - `predict_age_final_results_2025q3`
  - `predict_age_final_results_with_confidence` (view)
  - `predict_age_full_evaluation_raw_378m`
  - `predict_age_training_raw_14m`
  - `predict_age_training_targets_14m`

### ❌ What's Missing
- **All S3 data directories** under `s3://${S3_BUCKET}/predict-age/`
- **Missing Athena tables:**
  - `predict_age_staging_parsed_features_2025q3`
  - `predict_age_real_training_features_14m`
  - `predict_age_full_evaluation_features_378m`
- **Model files:** `s3://${S3_BUCKET}/predict-age/models/` (ridge, xgboost, qrf)
- **Prediction results:** All intermediate and final prediction outputs

---

## ✅ Recovery Strategy

**Good News:** The source table still exists! Everything can be regenerated.

**Recovery Order:**
1. ✅ Verify source table exists (already done)
2. ✅ Verify/Recreate database (already exists)
3. 🔄 Recreate staging table (378M rows, ~15-20 min, $0.50)
4. 🔄 Recreate training features (14M rows, ~3-5 min, $0.02)
5. 🔄 Recreate training targets (14M rows, ~2-3 min, $0.01)
6. 🔄 Recreate evaluation features (378M rows, ~12-15 min, $0.05)
7. ⚠️ Retrain models (run training Step Functions)
8. ⚠️ Regenerate predictions (run full pipeline)

**Total Recovery Time:** ~45-60 minutes  
**Total Recovery Cost:** ~$0.60-0.70 (Athena queries only)

---

## 🚀 Quick Recovery (Automated)

### Option 1: Run Recovery Script

```bash
cd /Users/rb/github/ai-app-predict-age
./scripts/recover_s3_athena_resources.sh
```

**What it does:**
- ✅ Verifies source table exists
- ✅ Checks database exists
- ✅ Recreates all missing tables in correct order
- ✅ Skips tables that already have data
- ✅ Provides progress updates

**Output:**
- Colored logs for each step
- Time estimates for each query
- Summary of what was recovered

---

## 🔧 Manual Recovery (Step-by-Step)

### Step 1: Verify Source Data

```bash
# Check source table exists (configure SOURCE_DATABASE and SOURCE_TABLE)
aws athena get-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name ${SOURCE_DATABASE} \
  --table-name ${SOURCE_TABLE} \
  --region us-east-1

# Verify database exists
aws athena get-database \
  --catalog-name AwsDataCatalog \
  --database-name ${DATABASE_NAME} \
  --region us-east-1
```

### Step 2: Recreate Staging Table (378M rows)

**Time:** ~15-20 minutes  
**Cost:** ~$0.50  
**Dependency:** Source table

```bash
cd /Users/rb/github/ai-app-predict-age

aws athena start-query-execution \
  --query-string "$(cat sql/02_ai_agent_kb_predict_age_predict_age_staging_parsed_features_2025q3.sql)" \
  --query-execution-context Database=${DATABASE_NAME} \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
  --work-group primary \
  --region us-east-1
```

**Wait for completion**, then verify:

```bash
aws athena list-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name ${DATABASE_NAME} \
  --table-name predict_age_staging_parsed_features_2025q3 \
  --region us-east-1
```

### Step 3: Recreate Training Features (14M rows)

**Time:** ~3-5 minutes  
**Cost:** ~$0.02  
**Dependency:** Staging table

```bash
aws athena start-query-execution \
  --query-string "$(cat sql/03_ai_agent_kb_predict_age_predict_age_real_training_features_14m.sql)" \
  --query-execution-context Database=${DATABASE_NAME} \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
  --work-group primary \
  --region us-east-1
```

### Step 4: Recreate Training Targets (14M rows)

**Time:** ~2-3 minutes  
**Cost:** ~$0.01  
**Dependency:** Source table

```bash
aws athena start-query-execution \
  --query-string "$(cat sql/04_ai_agent_kb_predict_age_predict_age_real_training_targets_14m.sql)" \
  --query-execution-context Database=${DATABASE_NAME} \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
  --work-group primary \
  --region us-east-1
```

### Step 5: Recreate Evaluation Features (378M rows)

**Time:** ~12-15 minutes  
**Cost:** ~$0.05  
**Dependency:** Staging table

```bash
aws athena start-query-execution \
  --query-string "$(cat sql/05_ai_agent_kb_predict_age_predict_age_full_evaluation_features_378m.sql)" \
  --query-execution-context Database=${DATABASE_NAME} \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
  --work-group primary \
  --region us-east-1
```

---

## 🔄 Post-Recovery: Regenerate Models & Predictions

After base tables are recovered, you need to:

### 1. Retrain Models

The training Fargate container will:
- Load training features and targets
- Train Ridge, XGBoost, and Quantile Forest models
- Save models to `s3://${S3_BUCKET}/predict-age/models/`

**Run:** Step Functions execution for training stage

### 2. Regenerate Predictions

The full pipeline will:
- Create predictions table (Lambda)
- Run 898 parallel prediction tasks (Fargate)
- Create human QA table (Lambda)
- Create final results table (Lambda)

**Run:** Complete Step Functions pipeline execution

---

## ✅ Verification Checklist

After recovery, verify:

```bash
# 1. Check all tables exist
aws athena list-table-metadata \
  --catalog-name AwsDataCatalog \
  --database-name ${DATABASE_NAME} \
  --region us-east-1

# 2. Check S3 data exists
aws s3 ls s3://${S3_BUCKET}/predict-age/ --recursive | head -20

# 3. Verify table row counts
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) as count FROM ${DATABASE_NAME}.predict_age_staging_parsed_features_2025q3" \
  --query-execution-context Database=${DATABASE_NAME} \
  --result-configuration OutputLocation=s3://${S3_BUCKET}/athena-results/ \
  --work-group primary \
  --region us-east-1
```

---

## 📋 Expected Tables After Recovery

| Table Name | Rows | Status |
|-----------|-------|--------|
| `predict_age_staging_parsed_features_2025q3` | 378M | ✅ Recreated |
| `predict_age_real_training_features_14m` | 14M | ✅ Recreated |
| `predict_age_real_training_targets_14m` | 14M | ✅ Recreated |
| `predict_age_full_evaluation_features_378m` | 378M | ✅ Recreated |
| `predict_age_predictions_2025q3` | 378M | ⚠️ Created by pipeline |
| `predict_age_human_qa_2025q3` | 378M | ⚠️ Created by pipeline |
| `predict_age_final_results_2025q3` | 378M | ⚠️ Created by pipeline |

---

## 🚨 Important Notes

1. **Models are gone:** You'll need to retrain (run training Step Functions)
2. **Predictions are gone:** You'll need to regenerate (run full pipeline)
3. **Lambda-created tables:** These will be recreated automatically during pipeline execution
4. **No data loss:** Source table is intact, so all data can be regenerated
5. **Cost:** Recovery is cheap (~$0.60), but full pipeline rerun costs ~$15

---

## 📞 Support

If recovery fails:
1. Check Athena query execution errors in AWS Console
2. Verify IAM permissions for Athena and S3
3. Check CloudWatch logs for Lambda functions
4. Review SQL files for syntax errors

---

**Status:** ✅ Recovery script ready  
**Last Updated:** October 23, 2025

