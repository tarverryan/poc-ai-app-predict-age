# Cursor AI Prompt: Implement Age Prediction ML Pipeline

**Purpose:** This document provides instructions for Cursor AI to implement the Age Prediction ML pipeline based on the proven job-change architecture.

**Context:** You are helping implement a new GitHub repo (`app-ai-predict-age`) that predicts employee age using the same proven architecture as the job-change project (`app-ai-predict-job-change`).

---

## 🎯 Project Overview

**Goal:** Predict age for 378M contacts using XGBoost regression (or Ridge/Quantile Forest after A/B test)

**Outputs:**
- `age_prediction` (integer, e.g., 23, 55, 67)
- `age_prediction_score` (confidence, 0-1 scale)

**Architecture:** Clone `app-ai-predict-job-change` and adapt for age prediction

---

## 🏗️ Naming Conventions (Critical!)

**Follow these naming patterns EXACTLY to match the job-change project structure:**

### Infrastructure Naming
- **Database**: `ai_agent_kb_predict_age`
- **S3 Data Path**: `s3://${S3_BUCKET}/predict-age/`
- **S3 Results Path**: `s3://${S3_BUCKET}/athena-results/` (shared with job-change)
- **Terraform State**: `s3://${TERRAFORM_STATE_BUCKET}/predict_age/`
- **Lambda Path**: `/Users/rb/github/app-ai-predict-age/lambda-predict-age/`
- **Fargate Path**: `/Users/rb/github/app-ai-predict-age/fargate-predict-age/`

### Resource Naming Patterns
- **Tables**: `predict_age_{table_name}_2025q3`
  - Example: `predict_age_predictions_2025q3`
  - Example: `predict_age_human_qa_2025q3`
  - Example: `real_training_features_14m`
  - Example: `real_training_targets_14m`
  - Example: `full_evaluation_features_378m`

- **Lambdas**: `ai-agent-predict-age-{function_name}`
  - Example: `ai-agent-predict-age-precleanup`
  - Example: `ai-agent-predict-age-feature-engineering`
  - Example: `ai-agent-predict-age-batch-generator`
  - Example: `ai-agent-predict-age-create-predictions-table`
  - Example: `ai-agent-predict-age-human-qa`
  - Example: `ai-agent-predict-age-final-results`
  - Example: `ai-agent-predict-age-cleanup`

- **Fargate Resources**: `fargate-predict-age-{resource_type}`
  - ECS Cluster: `fargate-predict-age`
  - Task Definitions: `ai-agent-predict-age-training`, `ai-agent-predict-age-prediction`
  - ECR Repos: `ai-agent-predict-age-training`, `ai-agent-predict-age-prediction`

- **IAM Roles**: `fargate-predict-age-{role_type}`
  - Example: `fargate-predict-age-execution-role`
  - Example: `fargate-predict-age-task-role`
  - Example: `fargate-predict-age-step-functions-role`

- **CloudWatch Log Groups**: `/ecs/ai-agent-predict-age-{task_name}`
  - Example: `/ecs/ai-agent-predict-age-training`
  - Example: `/ecs/ai-agent-predict-age-prediction`
  - Lambda logs: `/aws/lambda/ai-agent-predict-age-{function_name}`

- **Step Functions**: `ai-agent-predict-age-pipeline`

- **S3 Folder Structure**:
  ```
  s3://${S3_BUCKET}/predict-age/
  ├── features/
  │   ├── real_training_features_14m/
  │   └── full_evaluation_features_378m/
  ├── targets/
  │   └── real_training_targets_14m/
  ├── models/
  │   ├── ridge_age_model.joblib
  │   ├── xgboost_age_model.joblib
  │   └── qrf_age_model.joblib
  ├── evaluation/
  │   └── evaluation_metrics.json
  ├── predictions/
  │   └── predictions_*.jsonl
  ├── human-qa/
  │   └── predict_age_human_qa_2025q3/
  └── final-results/
      └── predict_age_final_results_2025q3/
  ```

- **SQL Files**: `{table_name}.sql`
  - Example: `real_training_features_14m.sql`
  - Example: `real_training_targets_14m.sql`
  - Example: `full_evaluation_features_378m.sql`

### Folder Structure (Local)
```
app-ai-predict-age/
├── fargate-predict-age/
│   ├── ai-agent-predict-age-training/
│   │   ├── Dockerfile
│   │   ├── training.py
│   │   └── requirements.txt
│   └── ai-agent-predict-age-prediction/
│       ├── Dockerfile
│       ├── prediction.py
│       └── requirements.txt
├── lambda-predict-age/
│   ├── ai-agent-predict-age-precleanup/
│   ├── ai-agent-predict-age-feature-engineering/
│   ├── ai-agent-predict-age-batch-generator/
│   ├── ai-agent-predict-age-create-predictions-table/
│   ├── ai-agent-predict-age-human-qa/
│   ├── ai-agent-predict-age-final-results/
│   └── ai-agent-predict-age-cleanup/
├── terraform/
│   ├── main.tf
│   ├── fargate.tf
│   ├── lambda.tf
│   └── step_functions.tf
├── docs/
│   ├── requirements.md
│   ├── error-log.md
│   └── ...
├── build-fargate.sh
├── deploy-fargate.sh
├── run-pipeline.sh
├── monitor-pipeline.sh
├── precleanup.sh
├── cleanup.sh
├── test-pipeline.sh
├── README.md
└── app_ai_predict_age_requirements.md
```

---

## 📋 Essential Reading (In Order)

Before starting implementation, read these files in this exact order:

### 1. **Requirements Document** (Read First!)
**File:** `/Users/rb/github/app-ai-predict-job-change/app_ai_predict_age_requirements.md`

**Key Sections:**
- Executive Summary (lines 1-20)
- Data Sources (lines 50-95) - **0% NULL age data!**
- Feature Engineering (lines 100-240) - **15 features**
- Modeling Approach (lines 290-560) - **3 models: Ridge, XGBoost, Quantile Forest**
- Pipeline Architecture (lines 650-720)
- Cost Analysis (lines 850-890) - **~$12 per run**

**Critical Facts:**
- Training set: 14M known ages (10% sample of 141.7M)
- Evaluation set: 378M PIDs (100% coverage)
- Age range: 18-75 years (filter outliers)
- Features: 15 predictors (tenure, job level, compensation, LinkedIn activity, etc.)
- Cost: ~$12 per run, <1 hour end-to-end

### 2. **Job-Change Project Structure** (Reference Architecture)
**File:** `/Users/rb/github/app-ai-predict-job-change/README.md`

**Key Sections:**
- Architecture (lines 15-26) - Lambda, Fargate, Step Functions, Athena
- Project Structure (lines 36-56) - Folder layout
- Cost Analysis (lines 83-97) - Proven $11/run

**What to Clone:**
- ✅ Folder structure (fargate-*, lambda-*, terraform/, docs/)
- ✅ Build scripts (build-fargate.sh, deploy-fargate.sh, run-pipeline.sh)
- ✅ Terraform configs (all .tf files)
- ✅ Lambda function structure (7 functions)
- ✅ Step Functions definition (11-stage pipeline)

### 3. **Job-Change Requirements** (Architecture Patterns)
**File:** `/Users/rb/github/app-ai-predict-job-change/docs/requirements.md`

**Key Sections:**
- Functional Requirements (lines 36-72) - Lambda functions, Fargate tasks
- Infrastructure (lines 8-20) - Naming conventions
- Non-Functional Requirements (lines 73-88) - Cost, performance, security

**Patterns to Replicate:**
- Naming: `predict-job-change` → `predict-age`
- Database: `ai_agent_kb_predict_age`
- S3 Path: `s3://${S3_BUCKET}/predict-age/`
- Parallel batches: 898 × 1M records

### 4. **Q4 Update Notes** (Age Feature Context)
**File:** `/Users/rb/github/app-ai-predict-job-change/2025q4_update_notes.md`

**Key Sections:**
- Priority #3: Add Age Feature (lines 255-347)
- Age vs Turnover Patterns (lines 267-275)
- Age Data Quality (lines 277-289)

**Why This Matters:**
- Age is top-3 predictor for job-change (8-12% accuracy gain)
- This shows how age predictions integrate with job-change model
- Validates business value

---

## 🚀 Implementation Plan

### Phase 1: Setup New Repo (30 minutes)

**Step 1: Create GitHub Repo**
```bash
# On GitHub, create new repo: app-ai-predict-age
# Clone locally
cd ~/github
git clone https://github.com/tarverryan/poc-ai-app-predict-age.git
cd app-ai-predict-age
```

**Step 2: Copy Architecture from Job-Change**
```bash
# Copy entire structure (we'll rename later)
cd ~/github/app-ai-predict-job-change

# Copy folders
cp -r fargate-predict-job-change ../app-ai-predict-age/fargate-predict-age
cp -r lambda-predict-job-change ../app-ai-predict-age/lambda-predict-age
cp -r terraform ../app-ai-predict-age/terraform
cp -r docs ../app-ai-predict-age/docs

# Copy scripts
cp build-fargate.sh deploy-fargate.sh run-pipeline.sh monitor-pipeline.sh ../app-ai-predict-age/
cp precleanup.sh cleanup.sh test-pipeline.sh ../app-ai-predict-age/

# Copy config
cp .gitignore ../app-ai-predict-age/
cp README.md ../app-ai-predict-age/README-TEMPLATE.md

# Copy requirements doc
cp app_ai_predict_age_requirements.md ../app-ai-predict-age/
```

**Step 3: Global Rename (predict-job-change → predict-age)**
```bash
cd ../app-ai-predict-age

# Find all files with predict-job-change
find . -type f -name "*.py" -o -name "*.tf" -o -name "*.sh" -o -name "*.md" | \
  xargs grep -l "predict-job-change" | \
  xargs sed -i '' 's/predict-job-change/predict-age/g'

# Find all files with predict_job_change
find . -type f -name "*.py" -o -name "*.tf" -o -name "*.sql" | \
  xargs grep -l "predict_job_change" | \
  xargs sed -i '' 's/predict_job_change/predict_age/g'

# Rename folders
mv fargate-predict-age/ai-agent-predict-job-change-training fargate-predict-age/ai-agent-predict-age-training
mv fargate-predict-age/ai-agent-predict-job-change-prediction fargate-predict-age/ai-agent-predict-age-prediction

# Rename Lambda folders (7 functions)
cd lambda-predict-age
for dir in ai-agent-predict-job-change-*; do
  new_dir=$(echo "$dir" | sed 's/predict-job-change/predict-age/')
  mv "$dir" "$new_dir"
done
cd ..
```

---

### Phase 2: Update Feature Engineering (1-2 hours)

**Goal:** Replace job-change features with age-prediction features

**Files to Update:**

#### File 1: `lambda-predict-age/ai-agent-predict-age-feature-engineering/real_training_features_14m.sql`

**Action:** Replace entire SQL with age features from requirements (lines 110-240)

**Key Changes:**
```sql
-- Replace job-change features with age features
-- OLD: job_changes_last_2_years, industry_turnover_rate, email_engagement_score
-- NEW: tenure_months, job_level_encoded, job_seniority_score, compensation_encoded,
--      company_size_encoded, linkedin_activity_score, days_since_profile_update,
--      social_media_presence_score, email_engagement_score, industry_typical_age,
--      job_function_encoded, company_revenue_encoded, quarter,
--      tenure_job_level_interaction, comp_size_interaction

-- Target: 15 features total
```

**Sample Feature (copy from requirements):**
```sql
-- Job level (senior roles = older employees)
CASE job_level
    WHEN 'C-Team' THEN 4  -- Avg age 50+
    WHEN 'Manager' THEN 3  -- Avg age 40-50
    WHEN 'Staff' THEN 2    -- Avg age 30-40
    ELSE 1                 -- Avg age 20-30
END as job_level_encoded,
```

#### File 2: `lambda-predict-age/ai-agent-predict-age-feature-engineering/real_training_targets_14m.sql`

**Action:** Replace job-change target with age target

**Key Changes:**
```sql
-- OLD: Binary job_change_flag (0/1)
-- NEW: Continuous actual_age (18-75 years)

-- Replace this:
CASE 
    WHEN q3.job_title != q2.job_title OR q3.org_name != q2.org_name THEN 1
    ELSE 0
END as job_change_flag

-- With this:
CASE 
    WHEN birth_year IS NOT NULL AND CAST(birth_year AS INT) BETWEEN 1930 AND 2007 
        THEN 2025 - CAST(birth_year AS INT)
    WHEN approximate_age IS NOT NULL AND CAST(approximate_age AS INT) BETWEEN 18 AND 75 
        THEN CAST(approximate_age AS INT)
    ELSE NULL
END as actual_age
```

**Critical:** Filter outliers (keep ages 18-75 only)

---

### Phase 3: Update Training Code (1-2 hours)

**Goal:** Change from XGBoost Classifier to XGBoost Regressor (+ Ridge + Quantile Forest)

**File:** `fargate-predict-age/ai-agent-predict-age-training/training.py`

**Key Changes:**

1. **Import Changes:**
```python
# ADD these imports
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# REMOVE these imports
from sklearn.metrics import precision_score, recall_score  # Binary classification only
```

2. **Model Training:**
```python
# OLD: Binary classification
model = xgb.XGBClassifier(
    objective='binary:logistic',
    eval_metric='logloss',
    scale_pos_weight=3.2  # Class imbalance
)

# NEW: Regression (train 3 models!)
# Model 1: Ridge
model_ridge = Ridge(alpha=1.0, random_state=42)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_train)
model_ridge.fit(X_scaled, y_train)
save_model_to_s3(model_ridge, 'ridge_age_model.joblib')

# Model 2: XGBoost
model_xgb = xgb.XGBRegressor(
    objective='reg:squarederror',  # Regression!
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    random_state=42
)
model_xgb.fit(X_train, y_train)
save_model_to_s3(model_xgb, 'xgboost_age_model.joblib')

# Model 3: Quantile Forest
model_qrf = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    min_samples_leaf=50,
    random_state=42,
    n_jobs=-1
)
model_qrf.fit(X_train, y_train)
save_model_to_s3(model_qrf, 'qrf_age_model.joblib')
```

3. **Evaluation Metrics:**
```python
# OLD: Classification metrics
accuracy = accuracy_score(y_val, y_pred)
precision = precision_score(y_val, y_pred)
recall = recall_score(y_val, y_pred)
auc = roc_auc_score(y_val, y_pred_proba)

# NEW: Regression metrics
mae = mean_absolute_error(y_val, y_pred)
rmse = np.sqrt(mean_squared_error(y_val, y_pred))
r2 = r2_score(y_val, y_pred)

# Accuracy within ±5 years
within_5 = np.mean(np.abs(y_val - y_pred) <= 5) * 100
```

4. **Model Selection Logic:**
```python
# Compare all 3 models, choose best
models = {
    'ridge': (model_ridge, mae_ridge, r2_ridge),
    'xgboost': (model_xgb, mae_xgb, r2_xgb),
    'qrf': (model_qrf, mae_qrf, r2_qrf)
}

# Select best (see requirements doc, lines 470-504)
best_model = select_best_model(models)
logger.info(f"Selected model: {best_model['name']} (MAE: {best_model['mae']:.2f})")
```

---

### Phase 4: Update Prediction Code (1 hour)

**Goal:** Predict age (integer) instead of job_change_probability

**File:** `fargate-predict-age/ai-agent-predict-age-prediction/prediction.py`

**Key Changes:**

1. **Load Selected Model:**
```python
# OLD: Load single XGBoost classifier
model = joblib.load(BytesIO(model_obj['Body'].read()))

# NEW: Load whichever model was selected during training
# Check which model exists in S3
models_to_try = ['ridge_age_model.joblib', 'xgboost_age_model.joblib', 'qrf_age_model.joblib']
model = None
for model_name in models_to_try:
    try:
        model_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=f'predict-age/models/{model_name}')
        model = joblib.load(BytesIO(model_obj['Body'].read()))
        logger.info(f"Loaded model: {model_name}")
        break
    except:
        continue
```

2. **Prediction Logic:**
```python
# OLD: Binary classification
predictions = model.predict_proba(features)[:, 1]  # Probability of class 1
predicted_label = 'Y' if prob > 0.5 else 'N'

# NEW: Regression
predictions = model.predict(features)  # Age prediction (float)
predicted_age = int(np.round(predictions))  # Round to integer

# Cap predictions to valid range
predicted_age = max(18, min(75, predicted_age))
```

3. **Confidence Score:**
```python
# For Ridge: Use standard error
if model_type == 'ridge':
    # Standard error from residuals
    confidence_score = 1.0 / (1.0 + standard_error / 10.0)

# For XGBoost: Use prediction intervals (if available)
elif model_type == 'xgboost':
    # Load quantile models if available
    confidence_score = 1.0 / (pred_upper - pred_lower + 1.0)

# For Quantile Forest: Native intervals
elif model_type == 'qrf':
    # Calculate from tree predictions
    tree_preds = [tree.predict(features) for tree in model.estimators_]
    pred_lower = np.percentile(tree_preds, 5, axis=0)
    pred_upper = np.percentile(tree_preds, 95, axis=0)
    confidence_score = 1.0 / (pred_upper - pred_lower + 1.0)
```

4. **Output Schema:**
```python
# OLD: job_change_prediction, job_change_prediction_score
# NEW: age_prediction, age_prediction_score

prediction_record = {
    'pid': str(pid),
    'age_prediction': int(predicted_age),  # Integer age
    'age_prediction_score': float(confidence_score),  # 0-1 confidence
    'prediction_ts': datetime.now().isoformat(),
    'model_version': model_version
}
```

---

### Phase 5: Update Terraform (30 minutes)

**Goal:** Rename all resources from predict-job-change to predict-age

**Files to Update:**
- `terraform/main.tf`
- `terraform/fargate.tf`
- `terraform/lambda.tf`
- `terraform/step_functions.tf`

**Global Changes:**
```hcl
# OLD
resource "aws_ecs_cluster" "main" {
  name = "fargate-predict-job-change"
}

# NEW
resource "aws_ecs_cluster" "main" {
  name = "fargate-predict-age"
}

# OLD
database_name = "ai_agent_kb_predict_job_change"

# NEW
database_name = "ai_agent_kb_predict_age"

# OLD
s3_bucket = "${S3_BUCKET}/predict-job-change/"

# NEW
s3_bucket = "${S3_BUCKET}/predict-age/"
```

**Critical Updates:**
1. Update all IAM role names
2. Update all Lambda function names (7 functions)
3. Update all ECR repository names (2 repos)
4. Update all CloudWatch log group names
5. Update Step Functions state machine name

---

### Phase 6: Test Locally (Optional, 1 hour)

**Goal:** Test feature engineering SQL and training code locally before deploying

**Step 1: Test Feature Engineering SQL**
```bash
# Run SQL in Athena console manually
# Copy SQL from real_training_features_14m.sql
# Verify 15 features are created
# Check row count (~14M expected)
```

**Step 2: Test Training Locally (if Docker available)**
```bash
cd fargate-predict-age/ai-agent-predict-age-training

# Build Docker image
docker build -t predict-age-training .

# Run with AWS credentials
docker run --rm \
  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
  -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
  -e DATABASE_NAME=ai_agent_kb_predict_age \
  -e S3_BUCKET=${S3_BUCKET} \
  predict-age-training
```

---

### Phase 7: Deploy to AWS (30 minutes)

**Goal:** Deploy infrastructure and run first training

**Step 1: Deploy Terraform**
```bash
cd terraform
terraform init
terraform plan  # Review changes
terraform apply -auto-approve
```

**Step 2: Build and Push Docker Images**
```bash
cd ..
./build-fargate.sh  # Builds both training and prediction images
```

**Step 3: Deploy Lambda Functions**
```bash
./deploy-fargate.sh  # Packages and deploys all 7 Lambda functions
```

**Step 4: Run Pipeline**
```bash
./run-pipeline.sh  # Triggers Step Functions execution
```

---

## 🎯 Key Differences from Job-Change (Cheat Sheet)

| Aspect | Job-Change | Age Prediction |
|--------|-----------|----------------|
| **Target** | Binary (Y/N) | Continuous (18-75) |
| **Model** | XGBoost Classifier | XGBoost Regressor (+ Ridge, QRF) |
| **Training Set** | 29.9M (Q2→Q3 changes) | 14M (known ages) |
| **Features** | 7 features | 15 features |
| **Target Variable** | job_change_flag (0/1) | actual_age (18-75) |
| **Evaluation** | AUC, precision, recall | MAE, RMSE, R² |
| **Confidence** | Probability (0-1) | Prediction interval width |
| **Database** | `ai_agent_kb_predict_job_change` | `ai_agent_kb_predict_age` |
| **S3 Path** | `predict-job-change/` | `predict-age/` |
| **Lambda Prefix** | `ai-agent-predict-job-change-*` | `ai-agent-predict-age-*` |
| **Fargate Prefix** | `fargate-predict-job-change` | `fargate-predict-age` |

---

## 🚨 Common Pitfalls (Watch Out!)

### Pitfall 1: Forgetting to Change Objective
```python
# ❌ WRONG (this is classification!)
model = xgb.XGBClassifier(objective='binary:logistic')

# ✅ CORRECT (regression!)
model = xgb.XGBRegressor(objective='reg:squarederror')
```

### Pitfall 2: Using Classification Metrics
```python
# ❌ WRONG (classification metrics for regression problem!)
accuracy = accuracy_score(y_val, y_pred)

# ✅ CORRECT (regression metrics!)
mae = mean_absolute_error(y_val, y_pred)
```

### Pitfall 3: Not Filtering Outliers
```sql
-- ❌ WRONG (includes ages 16-94)
SELECT CAST(approximate_age AS INT) as actual_age FROM ...

-- ✅ CORRECT (filter to 18-75)
WHERE actual_age BETWEEN 18 AND 75
```

### Pitfall 4: Not Rounding Age Predictions
```python
# ❌ WRONG (age as float: 34.7826)
age_prediction = model.predict(features)[0]

# ✅ CORRECT (age as integer: 35)
age_prediction = int(np.round(model.predict(features)[0]))
```

### Pitfall 5: Forgetting to Train 3 Models
```python
# ❌ WRONG (only training XGBoost)
model = train_xgboost(X_train, y_train)

# ✅ CORRECT (train all 3, compare)
model_ridge = train_ridge(X_train, y_train)
model_xgb = train_xgboost(X_train, y_train)
model_qrf = train_quantile_forest(X_train, y_train)
best_model = select_best_model(...)
```

---

## 📊 Success Criteria (How to Know You're Done)

### ✅ Phase 1 Complete: Setup
- [ ] New repo created: `app-ai-predict-age`
- [ ] All folders copied and renamed
- [ ] Global rename complete (no more `predict-job-change` references)

### ✅ Phase 2 Complete: Features
- [ ] SQL creates 15 features (not 7)
- [ ] SQL creates `actual_age` target (not `job_change_flag`)
- [ ] Age range filtered to 18-75 years
- [ ] Training set: ~14M records
- [ ] Features include: tenure_months, job_level_encoded, linkedin_activity_score, etc.

### ✅ Phase 3 Complete: Training
- [ ] 3 models train successfully (Ridge, XGBoost, QRF)
- [ ] All 3 models saved to S3
- [ ] Evaluation metrics calculated (MAE, RMSE, R²)
- [ ] Model selection logic works
- [ ] Training completes in ~26 minutes (vs 10 min for 1 model)

### ✅ Phase 4 Complete: Prediction
- [ ] Predictions are integers (18-75 range)
- [ ] Confidence scores calculated (0-1 scale)
- [ ] Output schema: `age_prediction`, `age_prediction_score`
- [ ] Predictions saved to S3 as JSONL

### ✅ Phase 5 Complete: Infrastructure
- [ ] Terraform apply succeeds
- [ ] All resources renamed correctly
- [ ] Database: `ai_agent_kb_predict_age`
- [ ] S3 path: `predict-age/`
- [ ] Step Functions pipeline defined

### ✅ Phase 6 Complete: End-to-End
- [ ] Pipeline runs without errors
- [ ] Training produces 3 models + metrics
- [ ] Predictions cover 378M PIDs (100%)
- [ ] Human QA table created
- [ ] Cost: ~$12 (expected)
- [ ] Time: <1 hour (expected)

### ✅ Phase 7 Complete: Validation
- [ ] MAE ≤ 5 years (at least 1 model)
- [ ] R² ≥ 0.75 (at least 1 model)
- [ ] Confidence scores calibrated
- [ ] Age distribution reasonable (median ~34, avg ~37)
- [ ] No systematic bias by industry/job level

---

## 🔧 Troubleshooting Guide

### Issue 1: "Table not found: real_training_features_14m"
**Cause:** Feature engineering Lambda didn't run or failed  
**Fix:** Check CloudWatch logs for feature-engineering Lambda, verify SQL syntax

### Issue 2: "Model training failed: All features must be numeric"
**Cause:** SQL created string features instead of numeric  
**Fix:** Add `CAST(... AS INT)` or `CAST(... AS DOUBLE)` to all features

### Issue 3: "Predictions are all the same age (e.g., 37)"
**Cause:** Model didn't train properly, using mean age as fallback  
**Fix:** Check training logs, verify 14M training records loaded, check feature variance

### Issue 4: "Terraform apply failed: Resource already exists"
**Cause:** Didn't fully rename from predict-job-change to predict-age  
**Fix:** Run global rename again, check for leftover `predict-job-change` strings

### Issue 5: "Cost is $30 instead of $12"
**Cause:** Training all 3 models takes longer (26 min vs 10 min)  
**Fix:** This is expected! Training cost increased from $0.16 to ~$0.40, still cheap

---

## 💡 Pro Tips

### Tip 1: Test SQL in Athena Console First
Before deploying, test all SQL queries manually in Athena console. This catches syntax errors early.

### Tip 2: Use Deterministic Sampling for Testing
Sample 1% of data (`MOD(pid, 100) = 0`) for quick testing before full 14M run.

### Tip 3: Monitor First Run Closely
Watch CloudWatch logs for first end-to-end run. Catch issues early before 898 parallel tasks run.

### Tip 4: Compare Model Performance Early
After first training, immediately compare Ridge vs XGBoost vs QRF. Don't wait for full prediction run.

### Tip 5: Document Selected Model
In evaluation metrics JSON, clearly document which model was selected and why.

---

## 📚 Reference Files (Copy-Paste Ready)

### Quick Reference: 15 Age Features (in order)
1. `tenure_months` - Months in current role
2. `job_level_encoded` - Job level (1-4)
3. `job_seniority_score` - Job title seniority (1-5)
4. `compensation_encoded` - Compensation range (3-8)
5. `company_size_encoded` - Company size (4-9)
6. `linkedin_activity_score` - LinkedIn connections (0.3-1.0)
7. `days_since_profile_update` - Profile recency
8. `social_media_presence_score` - Social media (0.2-1.0)
9. `email_engagement_score` - Email presence (0.0-1.0)
10. `industry_typical_age` - Industry age baseline (35-50)
11. `job_function_encoded` - Job function (0-5)
12. `company_revenue_encoded` - Revenue range (5-9)
13. `quarter` - Quarter of year (1-4)
14. `tenure_job_level_interaction` - Tenure × Job Level
15. `comp_size_interaction` - Compensation × Company Size

### Quick Reference: Expected Performance
- **Ridge:** MAE 6-8 years, R² 0.65-0.70, Training <1 min
- **XGBoost:** MAE 4-5 years, R² 0.75-0.80, Training 8-10 min
- **Quantile Forest:** MAE 5-6 years, R² 0.72-0.77, Training 12-15 min

### Quick Reference: File Rename Checklist
- [ ] `fargate-predict-age/` (folder)
- [ ] `lambda-predict-age/` (folder)
- [ ] `ai-agent-predict-age-*` (7 Lambda functions)
- [ ] `ai_agent_kb_predict_age` (database name)
- [ ] `predict-age/` (S3 path)
- [ ] All .py files (imports, variable names)
- [ ] All .tf files (resource names)
- [ ] All .sql files (table names)
- [ ] All .sh files (script variables)

---

## 🎓 Learning Resources

If you get stuck, refer to these sections in the requirements doc:

- **Feature Engineering:** Lines 110-240
- **Model Configurations:** Lines 302-551
- **Training Strategy:** Lines 553-568
- **Confidence Scoring:** Lines 515-551
- **Pipeline Architecture:** Lines 650-720
- **Cost Analysis:** Lines 850-890
- **Risks & Mitigations:** Lines 940-1010

---

## ✅ Final Checklist (Before Asking for Review)

### Code Quality
- [ ] All `predict-job-change` references renamed to `predict-age`
- [ ] No hardcoded values (use environment variables)
- [ ] Error handling for all S3/Athena operations
- [ ] Logging at INFO level for all major steps
- [ ] Comments explain "why", not "what"

### Testing
- [ ] Feature SQL runs in Athena (returns ~14M records)
- [ ] Target SQL runs in Athena (ages 18-75 only)
- [ ] Training completes (3 models saved to S3)
- [ ] Prediction completes (1 test batch)
- [ ] End-to-end pipeline completes

### Documentation
- [ ] README.md updated with age prediction details
- [ ] requirements.md accurate
- [ ] Error log started (docs/error-log.md)
- [ ] Cost analysis validated ($12 actual vs estimated)

### Infrastructure
- [ ] Terraform plan shows correct resources
- [ ] No leftover job-change resources
- [ ] IAM permissions least-privilege
- [ ] CloudWatch alarms set ($20 threshold)

---

## 🚀 You're Ready!

**Estimated Total Time:** 6-8 hours (for experienced developer with Cursor AI)

**Estimated Cost:** $12 first run + $0.50 testing = ~$13 total

**Expected Result:** Production-ready age prediction pipeline that:
- ✅ Predicts age for 378M contacts
- ✅ Provides confidence scores
- ✅ Runs in <1 hour
- ✅ Costs ~$12 per run
- ✅ Achieves MAE ≤5 years (XGBoost or QRF)

---

**Good luck! Ask questions early and often. The architecture is proven, so trust the patterns from job-change project.** 🎯

---

---

## 🤖 Bedrock Knowledge Base Integration

**Purpose:** Create comprehensive documentation for a Bedrock Agent to review and query age prediction results using natural language.

**Reference Project:** `s3://${S3_BUCKET}/predict-job-change/agent-context-upload/`

---

### Knowledge Base Structure

**Local Folder:** `/docs/bedrock-agent/kb-source/`  
**S3 Upload Path:** `s3://${S3_BUCKET}/predict-age/agent-context-upload/`  
**Embedding Model:** Amazon Titan Embeddings v2  
**Knowledge Base Type:** S3 vectorization for Bedrock Agent

---

### Required Documentation Files (13 documents)

**All documents created in:** `/docs/bedrock-agent/kb-source/`

| File | Purpose | Style |
|------|---------|-------|
| `00-knowledge-base-manifest.md` | Index of all documents, relationships, usage | Manifest/index |
| `01-model-overview.md` | Complete model summary, accuracy, use cases | Executive overview |
| `02-features.md` | All 22 features with detailed descriptions | Technical reference |
| `03-interpreting-confidence.md` | Confidence scores (dual scoring system) | User guide |
| `04-data-schema.md` | Athena tables, columns, SQL patterns | Technical reference |
| `05-faq.md` | Common questions and answers | Q&A format |
| `06-example-queries.md` | SQL query examples (20+ queries) | Code examples |
| `07-business-guidelines.md` | Use case guidance, thresholds, best practices | Business guide |
| `08-troubleshooting.md` | Error resolution, performance tips | Troubleshooting |
| `09-pipeline-architecture.md` | Technical architecture, components, flow | Technical deep-dive |
| `10-cost-and-performance.md` | Cost analysis, optimization, scaling | Operations guide |
| `11-quick-start.md` | 5-minute getting started guide | Quick reference |
| `12-model-performance.md` | Accuracy metrics, benchmarks, validation | Technical analysis |

---

### Content Requirements

**Tone and Style:**
- **Professional but conversational** - Like a senior data scientist explaining to a colleague
- **Comprehensive yet accessible** - Technical details with plain-language explanations
- **Action-oriented** - Provide concrete examples and SQL queries
- **Evidence-based** - Cite specific metrics, file paths, and commands

**Format Standards:**
- Markdown with clear headers (H2, H3)
- Code blocks with syntax highlighting (```sql, ```python)
- Tables for comparisons and metrics
- Bullet points for lists
- Examples with actual data/PIDs (sanitized)

**Cross-References:**
- Link between documents (e.g., "See `02-features.md` for details")
- Reference specific sections (e.g., "See Model Architecture in `09-pipeline-architecture.md`")
- Point to external resources (GitHub, S3 paths, Athena queries)

---

### Key Topics to Cover

**1. Model Performance (Actual Results)**
- MAE: 2.23 years (excellent)
- R²: 0.739 (strong)
- 378M PIDs with 100% coverage
- 83.2% high quality (≥60% confidence)
- Q3 2025 production data

**2. Dual Confidence Scoring System**
- `confidence_score_original`: -17.9 to 74.3 (interval width, lower = better)
- `confidence_pct`: 0-100% (percentage, higher = better)
- Formula: `max(0, 100 - abs(original) * 3.33)`
- 100% = real data or extremely confident ML
- Negative scores = excellent predictions (quantile crossing)

**3. Data Sources**
- Real Data: 141.7M PIDs (37.5%) - birth_year or approximate_age
- ML Predictions: 236.3M PIDs (62.5%) - XGBoost generated
- Smart Filtering: Only predict for PIDs missing age data
- Priority: real data > ML predictions > default (35)

**4. Production Metrics**
- Pipeline Runtime: ~45 minutes (training 15 min, prediction 25 min)
- Cost: $15 per run ($60/year for quarterly runs)
- Parallel Processing: 898 Fargate tasks (max 500 concurrent)
- Training Data: 14M PIDs with known ages
- Model: XGBoost Regressor (primary), Ridge (baseline), Quantile Forest (confidence)

**5. Business Use Cases**
- Marketing segmentation (age cohorts)
- Profile enrichment (fill missing ages)
- ML features (input for other models like job-change prediction)
- Demographics analysis
- Audience targeting

**6. Confidence Thresholds**
- **100%:** Real data only (legal/compliance)
- **80%+:** Personalized email, high-accuracy applications
- **60%+:** Standard segmentation, demographics analysis
- **40%+:** Broad segmentation, low-risk applications

---

### Reference Project Analysis

**Analyzed:** `s3://${S3_BUCKET}/predict-job-change/agent-context-upload/`

**Document Style Observations:**
- Heavy use of tables for metrics and comparisons
- SQL examples in every technical document
- Clear "TL;DR" or "Quick Reference" sections
- Real examples with actual values (not placeholders)
- Explicit file paths and S3 locations
- Cross-references between documents
- Business context + technical details balanced

**Mirror These Patterns:**
- Start with executive summary
- Provide concrete SQL queries (not pseudo-code)
- Use actual metrics from production (not estimates)
- Include troubleshooting sections
- Reference specific files and S3 paths
- Explain "why" decisions were made (e.g., "Why XGBoost?")

---

### Bedrock Agent Usage Scenarios

**Agent Will Answer Questions Like:**
- "What's the average confidence score for predictions?"
- "How do I query ages for PIDs in the 30-40 range?"
- "What's the difference between confidence_score_original and confidence_pct?"
- "Show me the SQL to filter high-quality predictions"
- "What confidence threshold should I use for email campaigns?"
- "How much does it cost to run the pipeline?"
- "What features are most important for predictions?"
- "Why do some PIDs have negative confidence scores?"

**Agent Needs to Retrieve:**
- SQL query examples (document 06)
- Confidence interpretation (document 03)
- Schema details (document 04)
- Cost analysis (document 10)
- Feature descriptions (document 02)
- Troubleshooting steps (document 08)

---

### Manual Upload Process

**After KB Creation:**
1. Verify all 13 documents in `/docs/bedrock-agent/kb-source/`
2. Manual upload to S3:
   ```bash
   aws s3 sync /Users/rb/github/ai-app-predict-age/docs/bedrock-agent/kb-source/ \
     s3://${S3_BUCKET}/predict-age/agent-context-upload/ \
     --exclude "*.DS_Store"
   ```
3. Configure Bedrock Knowledge Base:
   - Data source: S3 bucket
   - S3 URI: `s3://${S3_BUCKET}/predict-age/agent-context-upload/`
   - Chunking strategy: Default
   - Embedding model: amazon.titan-embed-text-v2
4. Sync Knowledge Base (trigger vectorization)
5. Create Bedrock Agent with Knowledge Base attached
6. Test agent with sample queries

---

### Success Criteria - Knowledge Base

- [ ] All 13 documents created in `/docs/bedrock-agent/kb-source/`
- [ ] 00-knowledge-base-manifest.md lists all documents
- [ ] Each document follows style guidelines (professional, comprehensive)
- [ ] SQL examples use actual table names (`predict_age_final_results_with_confidence`)
- [ ] Metrics reflect actual production data (2.23 MAE, 378M PIDs, 83% high quality)
- [ ] Cross-references work (link to other documents)
- [ ] Confidence scoring fully explained (dual system, negative scores, thresholds)
- [ ] Business use cases with concrete SQL examples
- [ ] Troubleshooting covers common issues
- [ ] Documents ready for manual S3 upload (no placeholders or TODOs)

---

**Document Created:** October 19, 2025  
**Last Updated:** October 23, 2025  
**Version:** 1.1  
**Status:** Ready for Implementation + KB Complete

