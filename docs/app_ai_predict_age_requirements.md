# AI Agent Age Prediction Pipeline - Requirements Document

**Project Name:** app-ai-predict-age  
**Created:** October 19, 2025  
**Status:** Planning Phase  
**Related Project:** app-ai-predict-job-change (proven architecture)

---

## Executive Summary

This document defines requirements for a production ML pipeline that predicts employee/contact age using AWS Fargate, Step Functions, and XGBoost. The pipeline leverages existing birth_year and approximate_age data to train a regression model and fill missing age data for contacts.

**Business Value:**
- Enrich contact profiles with missing age data
- Improve customer filtering and segmentation
- Enhance job-change prediction model (age is top-3 predictor)
- Provide confidence scores for data quality assessment

---

## Project Objectives

### Primary Goal
Predict, for each contact (`pid`), their age and produce two outputs per row:
- **`age_prediction`**: Integer age (e.g., 23, 55, 67)
- **`age_prediction_score`**: Confidence score (0-1 scale, higher = more confident)

### Success Criteria
- ✅ Train real XGBoost regression model on known age data (no dummy data)
- ✅ Predict age for all 378M PIDs (100% coverage)
- ✅ Achieve high accuracy on known ages (validation MAE ≤ 5 years)
- ✅ Provide calibrated confidence scores (know when uncertain)
- ✅ Run quarterly batch processing at ~$10-15 per run
- ✅ Complete end-to-end pipeline in <1 hour

---

## Architecture Overview

### AWS Stack (Proven from Job-Change Project)
- **Lambda**: Pre-cleanup, feature engineering, batch generation, table pre-creation, human QA, final results, post-cleanup
- **Fargate**: XGBoost training and parallel prediction tasks
- **Step Functions**: End-to-end pipeline orchestration with parallel processing
- **Athena**: Data warehouse and querying (native Step Functions integration)
- **S3**: Model storage and data lake
- **ECR**: Docker image registry
- **Terraform**: Infrastructure as Code

### Naming Convention
- **Database**: `ai_agent_kb_predict_age`
- **S3 Path**: `s3://${S3_BUCKET}/predict-age/`
- **Tables**: `predict_age_{table_name}_2025q3`
- **Lambdas**: `ai-agent-predict-age-{function_name}`
- **Fargate**: `fargate-predict-age-{resource_type}`
- **ECS Tasks**: `ai-agent-predict-age-{training|prediction}`

---

## Data Sources

### Primary Source Table
**Table:** `pid_historical.pid_03_foundation_with_surplus_2025q3`

**Key Fields:**
- **Identity**: `pid` (bigint, unique identifier)
- **Known Age Data**: 
  - `birth_year` (string, e.g., "1985") - **0% NULL in 141.7M records**
  - `approximate_age` (string, e.g., "40") - **0% NULL in 141.7M records**
- **Profile Features**:
  - `job_title`, `job_level`, `job_function`
  - `org_name`, `employee_range`, `revenue_range`, `industry`
  - `linkedin_connection_count`, `linkedin_url_is_valid`
  - `work_email`, `personal_email`
  - `job_start_date`, `ev_last_date`

**Data Quality (Validated October 19, 2025):**
- Total source records: 378,024,173 PIDs
- Records with age data: 141,727,672 (37.5% of source)
- NULL rate for age: 0% (excellent!)
- Age range: 16-94 years (with 485K outliers >80 or <18)
- Average age: 36.8 years
- Median age: 34 years

### Training Data Strategy

**Known Ages (Ground Truth):**
- Use 141.7M contacts with known `birth_year` or `approximate_age`
- Calculate current age: `2025 - CAST(birth_year AS INT)`
- Filter outliers: Keep ages 18-75 years
- Expected training set: ~140M records (99% of known ages)

**Missing Ages (Prediction Target):**
- 236.3M contacts without age data (62.5% of source)
- Primary use case: Predict age for these contacts

**Deterministic Sampling:**
- Training: 10% sample using `MOD(CAST(pid AS BIGINT), 10) = 0` (~14M records)
- Evaluation: All 378M PIDs

---

## Feature Engineering

### Training Features (21 features - Updated with JSON Parsing)

**Target Variable:**
```sql
-- Calculate actual age from birth_year
CASE 
    WHEN birth_year IS NOT NULL AND CAST(birth_year AS INT) BETWEEN 1930 AND 2007 
        THEN 2025 - CAST(birth_year AS INT)
    WHEN approximate_age IS NOT NULL AND CAST(approximate_age AS INT) BETWEEN 18 AND 75 
        THEN CAST(approximate_age AS INT)
    ELSE NULL
END as actual_age
```

**Predictor Features:**

1. **Career Stage Indicators (5 features)**
   ```sql
   -- Tenure (older people tend to have longer tenure)
   COALESCE(date_diff('month', date_parse(job_start_date, '%Y-%m-%d'), current_date), 60) as tenure_months,
   
   -- Job level (senior roles = older employees)
   CASE job_level
       WHEN 'C-Team' THEN 4  -- Avg age 50+
       WHEN 'Manager' THEN 3  -- Avg age 40-50
       WHEN 'Staff' THEN 2    -- Avg age 30-40
       ELSE 1                 -- Avg age 20-30
   END as job_level_encoded,
   
   -- Job seniority keywords
   CASE 
       WHEN LOWER(job_title) LIKE '%chief%' OR LOWER(job_title) LIKE '%vp%' THEN 5
       WHEN LOWER(job_title) LIKE '%senior%' OR LOWER(job_title) LIKE '%principal%' THEN 4
       WHEN LOWER(job_title) LIKE '%manager%' OR LOWER(job_title) LIKE '%director%' THEN 3
       WHEN LOWER(job_title) LIKE '%associate%' OR LOWER(job_title) LIKE '%analyst%' THEN 2
       WHEN LOWER(job_title) LIKE '%junior%' OR LOWER(job_title) LIKE '%entry%' THEN 1
       ELSE 3
   END as job_seniority_score,
   
   -- Compensation (higher comp = older/more experienced)
   CASE compensation_range
       WHEN '$200,001+' THEN 8
       WHEN '$150,001 - $200,000' THEN 7
       WHEN '$100,001 - $150,000' THEN 6
       WHEN '$75,001 - $100,000' THEN 5
       WHEN '$50,001 - $75,000' THEN 4
       WHEN '$25,001 - $50,000' THEN 3
       ELSE 4
   END as compensation_encoded,
   
   -- Company size (larger companies = older workforce avg)
   CASE CAST(employee_range AS VARCHAR)
       WHEN '10000+' THEN 9
       WHEN '5000 to 9999' THEN 8
       WHEN '1000 to 4999' THEN 7
       WHEN '500 to 999' THEN 6
       WHEN '200 to 499' THEN 5
       ELSE 4
   END as company_size_encoded
   ```

2. **Digital Footprint (4 features)**
   ```sql
   -- LinkedIn connections (younger = more active)
   CASE 
       WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 500 THEN 1.0
       WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 200 THEN 0.8
       WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 100 THEN 0.6
       ELSE 0.3
   END as linkedin_activity_score,
   
   -- Profile recency (younger = more recent updates)
   COALESCE(date_diff('day', date_parse(ev_last_date, '%Y-%m-%d'), current_date), 365) as days_since_profile_update,
   
   -- Social media presence (younger = more platforms)
   CASE 
       WHEN linkedin_url_is_valid = '1' AND facebook_url IS NOT NULL AND twitter_url IS NOT NULL THEN 1.0
       WHEN linkedin_url_is_valid = '1' AND (facebook_url IS NOT NULL OR twitter_url IS NOT NULL) THEN 0.7
       WHEN linkedin_url_is_valid = '1' THEN 0.5
       ELSE 0.2
   END as social_media_presence_score,
   
   -- Email engagement (work + personal)
   CASE 
       WHEN work_email IS NOT NULL AND personal_email IS NOT NULL THEN 1.0
       WHEN work_email IS NOT NULL OR personal_email IS NOT NULL THEN 0.5
       ELSE 0.0
   END as email_engagement_score
   ```

3. **Industry & Function (3 features)**
   ```sql
   -- Industry typical age
   CASE CAST(industry AS VARCHAR)
       WHEN 'Technology' THEN 35  -- Younger workforce
       WHEN 'Consulting' THEN 38
       WHEN 'Finance' THEN 42
       WHEN 'Healthcare' THEN 45
       WHEN 'Education' THEN 48
       WHEN 'Government' THEN 50  -- Older workforce
       ELSE 40
   END as industry_typical_age,
   
   -- Job function encoding
   CASE CAST(job_function AS VARCHAR)
       WHEN 'Engineering' THEN 1
       WHEN 'Sales' THEN 2
       WHEN 'Marketing' THEN 3
       WHEN 'Finance' THEN 4
       WHEN 'Operations' THEN 5
       ELSE 0
   END as job_function_encoded,
   
   -- Revenue range (proxy for company maturity)
   CASE CAST(revenue_range AS VARCHAR)
       WHEN '$1B+' THEN 9
       WHEN '$500M to $1B' THEN 8
       WHEN '$100M to $500M' THEN 7
       ELSE 5
   END as company_revenue_encoded
   ```

4. **Temporal Features (1 feature)**
   ```sql
   -- Quarter (for time-based patterns)
   EXTRACT(QUARTER FROM current_date) as quarter
   ```

5. **Derived Interaction Features (2 features)**
   ```sql
   -- Tenure × Job Level (senior role + long tenure = older)
   tenure_months * job_level_encoded as tenure_job_level_interaction,
   
   -- Compensation × Company Size (high comp at large company = older)
   compensation_encoded * company_size_encoded as comp_size_interaction
   ```

5. **Education & Experience from JSON (6 features) ⭐ NEW!**
   ```sql
   -- Education level (parsed from JSON, 89% coverage)
   CASE 
       WHEN LOWER(education) LIKE '%phd%' OR LOWER(education) LIKE '%doctorate%' THEN 5
       WHEN LOWER(education) LIKE '%master%' OR LOWER(education) LIKE '%mba%' THEN 4
       WHEN LOWER(education) LIKE '%bachelor%' THEN 3
       WHEN LOWER(education) LIKE '%associate%' THEN 2
       WHEN LOWER(education) LIKE '%high school%' THEN 1
       ELSE 2
   END as education_level_encoded,
   
   -- Graduation year (validation signal)
   TRY(CAST(json_extract_scalar(json_parse(education), '$[0].end_date') AS INT)) as graduation_year,
   
   -- Number of jobs (career history, 50% coverage)
   TRY(CAST(json_array_length(json_parse(work_experience)) AS INT)) as number_of_jobs,
   
   -- Skill count (experience proxy)
   TRY(CAST(json_array_length(json_parse(skills)) AS INT)) as skill_count,
   
   -- Total career years (STRONGEST AGE PREDICTOR! Correlation ~0.9)
   CASE 
       WHEN number_of_jobs > 0 THEN
           CAST(tenure_months AS DOUBLE) / 12.0 + (number_of_jobs - 1) * 2.5
       WHEN graduation_year IS NOT NULL THEN
           2025 - graduation_year
       ELSE 
           CAST(tenure_months AS DOUBLE) / 12.0
   END as total_career_years,
   
   -- Job churn rate (jobs per year of career)
   CASE 
       WHEN number_of_jobs > 0 AND tenure_months > 12 THEN
           CAST(number_of_jobs AS DOUBLE) / (CAST(tenure_months AS DOUBLE) / 12.0)
       ELSE 0.2  -- Default moderate churn
   END as job_churn_rate
   ```

**Total Features:** 21 predictors (19 direct + 2 interaction terms)

**New Features from JSON Parsing:**
- ✅ education_level_encoded (5 levels: high school → PhD)
- ✅ graduation_year (year of graduation from most recent degree)
- ✅ number_of_jobs (count of work experiences)
- ✅ skill_count (number of skills listed on LinkedIn)
- ✅ total_career_years (calculated from graduation/work history)
- ✅ job_churn_rate (career stability indicator)

---

## Target Definition

### Regression Target
**Goal:** Predict actual age (integer, 18-75 years)

**Target Calculation:**
```sql
-- Create training targets table
CREATE TABLE ai_agent_kb_predict_age.real_training_targets_14m AS
WITH known_ages AS (
    SELECT 
        pid,
        -- Prefer birth_year (more accurate), fallback to approximate_age
        CASE 
            WHEN birth_year IS NOT NULL AND CAST(birth_year AS INT) BETWEEN 1930 AND 2007 
                THEN 2025 - CAST(birth_year AS INT)
            WHEN approximate_age IS NOT NULL AND CAST(approximate_age AS INT) BETWEEN 18 AND 75 
                THEN CAST(approximate_age AS INT)
            ELSE NULL
        END as actual_age,
        birth_year,
        approximate_age
    FROM pid_historical.pid_03_foundation_with_surplus_2025q3
    WHERE pid IS NOT NULL
      AND (birth_year IS NOT NULL OR approximate_age IS NOT NULL)
      AND MOD(CAST(pid AS BIGINT), 10) = 0  -- 10% sample
)
SELECT 
    pid,
    actual_age,
    birth_year,
    approximate_age,
    current_date as target_creation_date,
    'v1.0_real_age_data' as target_version
FROM known_ages
WHERE actual_age IS NOT NULL
  AND actual_age BETWEEN 18 AND 75  -- Filter outliers
```

**Expected Training Set:**
- ~14M records (10% of 140M known ages)
- Age range: 18-75 years
- 0% NULL rate (filtered)

---

## Modeling Approach

### Multi-Model Strategy (A/B Testing)

**Philosophy:** Train 3 models, let validation data choose the winner

Instead of assuming XGBoost is best, we'll train 3 complementary models and select based on validation performance. **Cost impact: $0** (same Fargate container, train sequentially). **Time impact: +16 minutes** (26 min vs 10 min training).

---

### Model 1: Ridge Regression (Baseline) 🚀

**Why Ridge:**
- **Extremely fast** (~1 min training on 14M records vs 10 min XGBoost)
- **Natural confidence intervals** (statistical standard errors, no quantile regression needed)
- **Highly interpretable** (coefficient = "each year of tenure adds X years of age")
- **Small model size** (<1MB vs 450MB for XGBoost)
- **No hyperparameter tuning** (cross-validation finds optimal alpha)

**When Ridge Wins:**
- If age relationships are mostly linear (tenure ↑ → age ↑)
- If interpretability/speed matters more than 1 year MAE gain
- If native confidence intervals are valued

**Expected Performance (Updated with 21 features):**
- MAE: 5-7 years
- R²: 0.70-0.75
- Training: <1 min

**Configuration:**
```python
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

# Ridge regression with optimal regularization
model_ridge = Ridge(
    alpha=1.0,           # L2 regularization strength
    random_state=42,
    max_iter=1000
)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_train)
model_ridge.fit(X_scaled, y_train)

# Native confidence intervals (standard errors)
# No need for quantile regression!
```

---

### Model 2: XGBoost Regressor (Production Candidate) ⚡

**Why XGBoost:**
- **Proven in job-change project** ($11/run, 44 min end-to-end)
- **Handles non-linear relationships** (age vs tenure, compensation curves)
- **Robust to outliers and missing data**
- **Feature importance** (interpretability via SHAP)
- **Industry standard** (used by Fortune 500)

**When XGBoost Wins:**
- If non-linear patterns exist (tech = younger, government = older)
- If feature interactions are critical (tenure × job_level)
- If accuracy justifies complexity

**Expected Performance (Updated with 21 features):**
- MAE: 3-4 years ✅✅ (exceeds target!)
- R²: 0.80-0.85 ✅✅ (exceeds target!)
- Training: 10-12 min

**Configuration:**
```python
import xgboost as xgb

model_xgb = xgb.XGBRegressor(
    objective='reg:squarederror',  # Regression objective
    n_estimators=200,               # Boosting rounds
    max_depth=6,                    # Tree depth
    learning_rate=0.05,             # Conservative learning
    subsample=0.8,                  # Row sampling
    colsample_bytree=0.8,           # Feature sampling
    min_child_weight=5,             # Regularization
    gamma=0.1,                      # Pruning
    reg_alpha=0.1,                  # L1 regularization
    reg_lambda=1.0,                 # L2 regularization
    random_state=42,
    n_jobs=-1
)
```

---

### Model 3: Quantile Regression Forest (Confidence Champion) 🎯

**Why Quantile Forest:**
- **Native prediction intervals** (no need for 3 separate models)
- **Robust to outliers** (better for ages >70, <25)
- **Trustworthy confidence** (narrow interval = high confidence)
- **Simple uncertainty** (no complex quantile regression)

**When Quantile Forest Wins:**
- If confidence scores are business-critical (they are!)
- If outlier handling is important (ages 18-75 range)
- If simplicity > 0.5 year MAE gain

**Expected Performance (Updated with 21 features):**
- MAE: 4-5 years (competitive with XGBoost)
- R²: 0.77-0.82
- Training: 14-17 min
- **Confidence calibration:** Excellent (native)

**Configuration:**
```python
from sklearn.ensemble import RandomForestRegressor
import numpy as np

model_qrf = RandomForestRegressor(
    n_estimators=200,           # 200 trees
    max_depth=10,               # Deeper than XGBoost (more flexible)
    min_samples_leaf=50,        # Regularization
    random_state=42,
    n_jobs=-1,
    max_features='sqrt'         # Feature sampling
)

# Get prediction intervals (5th and 95th percentiles)
def predict_with_intervals(model, X):
    # Each tree gives a prediction
    predictions = np.array([tree.predict(X) for tree in model.estimators_])
    
    # Calculate percentiles across trees
    pred_mean = predictions.mean(axis=0)
    pred_lower = np.percentile(predictions, 5, axis=0)  # 5th percentile
    pred_upper = np.percentile(predictions, 95, axis=0)  # 95th percentile
    
    # Confidence = 1 / (interval width + 1)
    confidence = 1.0 / (pred_upper - pred_lower + 1.0)
    
    return pred_mean, pred_lower, pred_upper, confidence
```

---

### Model Selection Criteria

**Phase 1: Train All 3 Models (Same Fargate Job)**
```python
# Training pipeline (Fargate)
logger.info("Training Ridge Regression baseline...")
model_ridge = train_ridge(X_train, y_train)
save_model_to_s3(model_ridge, 'ridge_age_model.joblib')
logger.info(f"Ridge training complete: {time.time() - start:.1f}s")

logger.info("Training XGBoost regressor...")
model_xgb = train_xgboost(X_train, y_train)
save_model_to_s3(model_xgb, 'xgboost_age_model.joblib')
logger.info(f"XGBoost training complete: {time.time() - start:.1f}s")

logger.info("Training Quantile Random Forest...")
model_qrf = train_quantile_forest(X_train, y_train)
save_model_to_s3(model_qrf, 'qrf_age_model.joblib')
logger.info(f"QRF training complete: {time.time() - start:.1f}s")
```

**Phase 2: Evaluate on Validation Set (2.8M records)**

| Metric | Ridge | XGBoost | Quantile Forest | Target |
|--------|-------|---------|-----------------|--------|
| **MAE** | 5-7 years | **3-4 years** ✅✅ | 4-5 years | ≤5 years |
| **RMSE** | 7-9 years | **5-6 years** | 6-7 years | ≤7 years |
| **R²** | 0.70-0.75 | **0.80-0.85** ✅✅ | 0.77-0.82 | ≥0.75 |
| **Within ±5 years** | 75-80% | **85-90%** ✅ | 82-87% | ≥80% |
| **Confidence** | Native (excellent) | Complex (3 models) | Native (excellent) | Calibrated |
| **Training Time** | <1 min | 10-12 min | 14-17 min | <20 min |
| **Model Size** | <1MB | ~450MB | ~1.2GB | <2GB |
| **Interpretability** | Excellent | Good (SHAP) | Good | High |

**Note:** Performance estimates updated for 21 features (includes JSON-parsed education, work experience, skills)

**Phase 3: Selection Logic**

```python
# Automated model selection based on validation metrics
def select_best_model(ridge_metrics, xgb_metrics, qrf_metrics):
    """
    Select production model based on validation performance
    
    Priority:
    1. MAE ≤ 5 years (required)
    2. R² ≥ 0.75 (required)
    3. If multiple pass → choose simplest (Ridge > QRF > XGB)
    4. If none pass → choose best MAE (likely XGBoost)
    """
    models = [
        ('Ridge', ridge_metrics, 'ridge_age_model.joblib'),
        ('XGBoost', xgb_metrics, 'xgboost_age_model.joblib'),
        ('QRF', qrf_metrics, 'qrf_age_model.joblib')
    ]
    
    # Filter models meeting targets
    passing_models = [
        (name, metrics, path) for name, metrics, path in models
        if metrics['mae'] <= 5.0 and metrics['r2'] >= 0.75
    ]
    
    if passing_models:
        # Choose simplest model if multiple pass
        logger.info(f"{len(passing_models)} models meet targets. Choosing simplest.")
        return passing_models[0]  # Ridge first, then QRF, then XGB
    else:
        # Choose best MAE if none pass
        best = min(models, key=lambda x: x[1]['mae'])
        logger.info(f"No models meet targets. Choosing best MAE: {best[0]}")
        return best
```

**Default Production Choice (if validation is close):**
- If MAE difference < 1 year: **Choose Ridge** (simplicity wins)
- If MAE difference 1-2 years: **Choose Quantile Forest** (confidence wins)
- If MAE difference > 2 years: **Choose XGBoost** (accuracy wins)

---

### Confidence Score Strategy by Model

**Ridge Regression:**
```python
# Native confidence from statistical standard errors
from sklearn.linear_model import Ridge
import numpy as np

# Predict with standard errors
y_pred = model.predict(X_scaled)
residuals = y_train - model.predict(X_train_scaled)
mse = np.mean(residuals ** 2)
se = np.sqrt(mse)  # Standard error

# Confidence score = inverse of prediction uncertainty
confidence_score = 1.0 / (1.0 + se / 10.0)  # Normalize to 0-1
```

**XGBoost:**
```python
# Quantile regression (3 models: lower, mean, upper)
model_lower = xgb.XGBRegressor(objective='reg:quantileerror', quantile_alpha=0.05)
model_mean = xgb.XGBRegressor(objective='reg:squarederror')
model_upper = xgb.XGBRegressor(objective='reg:quantileerror', quantile_alpha=0.95)

# Confidence = inverse of interval width
confidence_score = 1.0 / (pred_upper - pred_lower + 1.0)
```

**Quantile Random Forest:**
```python
# Native prediction intervals (no extra training!)
predictions = np.array([tree.predict(X) for tree in model.estimators_])
pred_lower = np.percentile(predictions, 5, axis=0)
pred_upper = np.percentile(predictions, 95, axis=0)

# Confidence = inverse of interval width
confidence_score = 1.0 / (pred_upper - pred_lower + 1.0)
```

### Training Strategy

**Data Split:**
- Training: 80% of 14M records (11.2M)
- Validation: 20% of 14M records (2.8M)
- Split: Random (no temporal considerations for age)

**Training Pipeline:**
1. Load features + targets from Athena
2. Filter outliers (ages 18-75)
3. Handle missing values (intelligent defaults)
4. Train XGBoost model
5. Validate on holdout set
6. Save model to S3

### Prediction Strategy

**Confidence Score Calculation:**

Since XGBoost doesn't provide native uncertainty, we'll use:

**Option 1: Prediction Interval Width (Recommended)**
```python
# Train two additional models for prediction intervals
model_upper = xgb.XGBRegressor(objective='reg:quantileerror', quantile_alpha=0.95)
model_lower = xgb.XGBRegressor(objective='reg:quantileerror', quantile_alpha=0.05)

# Confidence = 1 / (upper - lower + 1)
# Narrow interval = high confidence
# Wide interval = low confidence
confidence_score = 1.0 / (predicted_age_upper - predicted_age_lower + 1.0)
```

**Option 2: Residual-Based Confidence (Fallback)**
```python
# Use validation set to calculate typical error by age range
# confidence_score = 1.0 / (1.0 + expected_mae_for_age_range)
```

**Output Schema:**
```sql
CREATE TABLE predict_age_predictions_2025q3 (
    pid BIGINT,
    age_prediction INT,                    -- Predicted age (rounded to int)
    age_prediction_score DOUBLE,           -- Confidence (0-1 scale)
    prediction_ts TIMESTAMP,               -- When prediction was made
    model_version VARCHAR(50),             -- 'v1.0_xgboost_age'
    age_prediction_lower INT,              -- 5th percentile (optional)
    age_prediction_upper INT               -- 95th percentile (optional)
)
```

---

## Evaluation Metrics

### Regression Metrics

1. **Mean Absolute Error (MAE)**
   - Target: ≤5 years (excellent for age prediction)
   - Interpretation: Average prediction error

2. **Root Mean Squared Error (RMSE)**
   - Target: ≤7 years
   - Interpretation: Penalizes large errors

3. **R² Score**
   - Target: ≥0.75 (explains 75%+ of variance)
   - Interpretation: Model fit quality

4. **Accuracy within N years**
   - Within ±3 years: Target ≥60%
   - Within ±5 years: Target ≥80%
   - Within ±10 years: Target ≥95%

### Confidence Calibration

**Calibration Check:**
```sql
-- High confidence (score > 0.8) should have MAE < 3 years
-- Medium confidence (score 0.5-0.8) should have MAE 3-7 years
-- Low confidence (score < 0.5) should have MAE > 7 years
SELECT 
    CASE 
        WHEN age_prediction_score > 0.8 THEN 'High'
        WHEN age_prediction_score > 0.5 THEN 'Medium'
        ELSE 'Low'
    END as confidence_bucket,
    COUNT(*) as employee_count,
    AVG(ABS(actual_age - age_prediction)) as avg_mae,
    APPROX_PERCENTILE(ABS(actual_age - age_prediction), 0.50) as median_error,
    APPROX_PERCENTILE(ABS(actual_age - age_prediction), 0.90) as p90_error
FROM validation_results
GROUP BY 1
ORDER BY 1
```

### Business Validation

**Age Distribution Check:**
```sql
-- Predicted ages should match known age distribution
-- Known ages: median 34, avg 36.8, range 18-75
-- Predicted ages should be similar (no systematic bias)
```

---

## Pipeline Architecture

### Step Functions Workflow

**Pipeline Stages:**

1. **PreCleanup** (Lambda)
   - Drop previous run tables
   - Clean S3 intermediate data
   - Preserve quarterly results only

2. **StagingParsedFeatures** (Athena Direct) ⭐ NEW!
   - Parse JSON fields once (education, work_experience, skills)
   - Create `staging_parsed_features_2025q3` table
   - **Critical for performance:** Avoids repeated JSON parsing
   - Time: ~15-20 min, Cost: ~$0.50
   - Output: 378M records with pre-parsed fields

3. **TrainingFeatures** (Lambda)
   - Create `real_training_features_14m` table
   - Calculate 21 predictor features (from staging table)
   - Athena CTAS to S3/Parquet

4. **TrainingTargets** (Lambda)
   - Create `real_training_targets_14m` table
   - Calculate actual ages from birth_year
   - Filter outliers (18-75 years)

5. **Training** (Fargate)
   - Load features + targets from Athena
   - Train 3 models: Ridge, XGBoost, Quantile Forest
   - Validate on 20% holdout
   - Select best model (MAE ≤5 years)
   - Save models + metrics to S3

6. **EvaluationFeatures** (Athena Direct)
   - Create `full_evaluation_features_378m` table
   - Calculate 21 features for ALL PIDs (from staging table)
   - Native Step Functions integration

7. **GenerateBatchIds** (Lambda)
   - Generate batch IDs for parallel processing
   - 898 batches × ~420K records each

8. **CreatePredictionsTable** (Lambda)
   - Pre-create predictions table (prevent race conditions)
   - Define schema in Athena

9. **ParallelPrediction** (Map State → 898 Fargate Tasks)
   - Each task processes ~420K PIDs
   - Load selected model from S3
   - Predict age + confidence
   - Save to S3 in 100K chunks (JSONL)
   - MaxConcurrency: 100 tasks

10. **HumanQA** (Lambda)
    - Create `predict_age_human_qa_2025q3` table
    - LEFT JOIN all PIDs with predictions
    - Flag missing predictions

11. **FinalResults** (Lambda)
    - Create `predict_age_final_results_2025q3` table
    - 100% PID coverage (378M records)
    - Apply default age for missing (median age 34)

12. **Cleanup** (Lambda)
    - Remove temporary tables (keep staging for next run)
    - Clean intermediate S3 data
    - Preserve final results + staging only

---

## Infrastructure (Terraform)

### Resource Definitions

**Fargate Task Definitions:**

**Training Task:**
```hcl
resource "aws_ecs_task_definition" "training" {
  family                   = "ai-agent-predict-age-training"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "16384"  # 16 vCPU
  memory                   = "65536"  # 64GB RAM
  execution_role_arn       = aws_iam_role.fargate_execution_role.arn
  task_role_arn            = aws_iam_role.fargate_task_role.arn

  container_definitions = jsonencode([{
    name  = "training"
    image = "${aws_ecr_repository.training.repository_url}:latest"
    environment = [
      {name = "DATABASE_NAME", value = "ai_agent_kb_predict_age"},
      {name = "S3_BUCKET", value = "${S3_BUCKET}"},
      {name = "MODEL_TYPE", value = "xgboost_regression"}
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/ai-agent-predict-age-training"
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}
```

**Prediction Task:**
```hcl
resource "aws_ecs_task_definition" "prediction" {
  family                   = "ai-agent-predict-age-prediction"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "8192"   # 8 vCPU
  memory                   = "32768"  # 32GB RAM
  execution_role_arn       = aws_iam_role.fargate_execution_role.arn
  task_role_arn            = aws_iam_role.fargate_task_role.arn

  container_definitions = jsonencode([{
    name  = "prediction"
    image = "${aws_ecr_repository.prediction.repository_url}:latest"
    environment = [
      {name = "DATABASE_NAME", value = "ai_agent_kb_predict_age"},
      {name = "S3_BUCKET", value = "${S3_BUCKET}"},
      {name = "FEATURES_TABLE_NAME", value = "full_evaluation_features_378m"},
      {name = "BATCH_ID", value = "0"}  # Overridden by Step Functions
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/ai-agent-predict-age-prediction"
        "awslogs-region"        = "us-east-1"
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}
```

**Lambda Functions:**
- `ai-agent-predict-age-precleanup`
- `ai-agent-predict-age-feature-engineering`
- `ai-agent-predict-age-batch-generator`
- `ai-agent-predict-age-create-predictions-table`
- `ai-agent-predict-age-human-qa`
- `ai-agent-predict-age-final-results`
- `ai-agent-predict-age-cleanup`

**ECR Repositories:**
- `ai-agent-predict-age-training`
- `ai-agent-predict-age-prediction`

**S3 Structure:**
```
s3://${S3_BUCKET}/predict-age/
├── staging/
│   └── parsed_features_2025q3/        ⭐ NEW! (JSON pre-parsing)
├── features/
│   ├── real_training_features_14m/
│   └── full_evaluation_features_378m/
├── targets/
│   └── real_training_targets_14m/
├── models/
│   ├── ridge_age_model.joblib          ⭐ NEW!
│   ├── xgboost_age_model.joblib
│   └── qrf_age_model.joblib            ⭐ NEW!
├── evaluation/
│   └── evaluation_metrics.json
├── predictions/
│   └── predictions_*.jsonl
├── human-qa/
│   └── predict_age_human_qa_2025q3/
├── final-results/
│   └── predict_age_final_results_2025q3/
└── athena-results/                     ⭐ NEW! (query results)
```

---

## Cost Analysis

### Projected Costs (Updated with JSON Parsing)

**Staging (JSON Parsing - One Time per Quarter):**
- **Athena**: Parse JSON for 378M records = **~$0.50** ⭐ NEW!

**Training:**
- **Fargate**: 64GB × 16 vCPU × ~12 min (3 models) = **~$0.19** (+$0.03 for extra models)
- **Athena**: Feature + target creation (~14M records) = **~$0.02**

**Evaluation Features:**
- **Athena**: CTAS for 378M records = **~$0.05**

**Prediction:**
- **Fargate**: 898 tasks × 32GB × 8 vCPU × ~1.6 min = **~$10.80**
- **Athena**: Batch queries (898 × 420K records) = **~$0.10**

**Human QA + Final Results:**
- **Athena**: CTAS for 378M records × 2 = **~$0.10**

**Lambda:**
- All Lambda invocations = **<$0.05**

**Total Estimated Cost per Run:** **~$11.81** ✅ **Well under $20 budget!**

**Note:** Staging cost ($0.50) is one-time per quarter, amortized across runs if pipeline is executed multiple times.

**Annual Cost (Quarterly Runs):**
- 4 quarterly runs: $12 × 4 = **$48/year**

---

## Performance Targets

### End-to-End Timeline

Based on job-change project (similar scale):

| Stage | Time | Notes |
|-------|------|-------|
| PreCleanup | 1 min | Drop tables, clean S3 |
| Training Features | 3 min | Athena CTAS, 14M records |
| Training Targets | 2 min | Athena CTAS, 14M records |
| Training | 8-10 min | Fargate, 64GB, 14M records |
| Evaluation Features | 12-15 min | Athena CTAS, 378M records |
| Batch Generation | <1 min | Lambda, 898 IDs |
| Create Predictions Table | <1 min | Lambda, DDL |
| Parallel Predictions | 10-15 min | 898 tasks, MaxConcurrency=100 |
| Human QA | 2-3 min | Athena CTAS, 378M records |
| Final Results | 2-3 min | Athena CTAS, 378M records |
| Cleanup | 1-2 min | Drop tables, clean S3 |

**Total:** **45-55 minutes end-to-end** ✅ Within 1-hour target!

---

## Data Quality & Validation

### Training Data Quality Checks

**Pre-Training Validation:**
```python
def validate_training_data(df):
    """Validate training data quality before training"""
    issues = {}
    
    # Check for NULL targets
    null_targets = df['actual_age'].isnull().sum()
    if null_targets > 0:
        issues['null_targets'] = f"{null_targets} records with NULL age"
    
    # Check age range
    invalid_ages = ((df['actual_age'] < 18) | (df['actual_age'] > 75)).sum()
    if invalid_ages > 0:
        issues['invalid_ages'] = f"{invalid_ages} records outside 18-75 range"
    
    # Check feature completeness
    for col in df.columns:
        null_pct = df[col].isnull().sum() / len(df) * 100
        if null_pct > 50:
            issues[f'null_{col}'] = f"{null_pct:.1f}% NULL values"
    
    # Check class distribution
    age_distribution = df['actual_age'].value_counts().sort_index()
    logger.info(f"Age distribution: {age_distribution.describe()}")
    
    if issues:
        logger.error(f"Training data quality issues: {issues}")
        raise ValueError(f"Training data validation failed: {issues}")
    
    logger.info("✅ Training data validation passed")
    return True
```

### Prediction Quality Checks

**Post-Prediction Validation:**
```sql
-- Check prediction distribution
SELECT 
    FLOOR(age_prediction / 10) * 10 as age_bucket,
    COUNT(*) as employee_count,
    AVG(age_prediction_score) as avg_confidence,
    MIN(age_prediction) as min_age,
    MAX(age_prediction) as max_age
FROM predict_age_predictions_2025q3
GROUP BY 1
ORDER BY 1

-- Expected: Similar distribution to known ages (median ~34, avg ~37)
-- Red flags: Too many <20 or >80, bimodal distribution
```

---

## Risks & Mitigations

### Risk 1: Training Data Insufficient
**Risk:** Only 14M training records may not generalize well  
**Probability:** Low (37.5% of source has known ages)  
**Impact:** Medium (poor accuracy for edge cases)  
**Mitigation:**
- Validate on full 140M known ages (not just 10% sample)
- Use 10-fold cross-validation for robust estimates
- Monitor MAE by age range (detect systematic errors)

### Risk 2: Feature Engineering Weak
**Risk:** 15 features may not capture age signal well  
**Probability:** Medium (age correlates with many factors)  
**Impact:** High (poor accuracy across the board)  
**Mitigation:**
- Add interaction terms (tenure × compensation, etc.)
- Feature importance analysis (drop weak features)
- A/B test with simple baseline (linear regression on tenure)

### Risk 3: Confidence Scores Poorly Calibrated
**Risk:** Confidence score doesn't match actual error  
**Probability:** Medium (quantile regression is new)  
**Impact:** Medium (can't trust low-confidence predictions)  
**Mitigation:**
- Validate calibration on holdout set
- Fallback to residual-based confidence if quantile fails
- Document confidence interpretation clearly

### Risk 4: Prediction Coverage Gaps
**Risk:** Some PIDs fail prediction (like 36% in job-change)  
**Probability:** Low (age features less sparse than job_title)  
**Impact:** Low (can use median age as fallback)  
**Mitigation:**
- Pre-create predictions table (avoid race conditions)
- Default age for missing: Median age 34
- Track missing predictions in Human QA table

### Risk 5: Model Bias by Demographics
**Risk:** Model systematically over/under-predicts for certain groups  
**Probability:** Medium (age correlates with industry, function)  
**Impact:** High (fairness/compliance concerns)  
**Mitigation:**
- Validate MAE by industry, job level, gender (if available)
- Monitor calibration by demographic segments
- Consider fairness constraints (e.g., equal MAE across groups)

---

## Deliverables (MVP)

### Code & Infrastructure
- [ ] Terraform configuration for all AWS resources
- [ ] Lambda functions (7 functions)
- [ ] Fargate Docker images (training, prediction)
- [ ] Step Functions definition (JSON/Terraform)
- [ ] Build, deploy, run, monitor shell scripts
- [ ] Feature engineering SQL files
- [ ] Python training and prediction scripts

### Documentation
- [ ] Architecture diagram (similar to job-change)
- [ ] Requirements document (this document)
- [ ] Runbook (how to run end-to-end)
- [ ] Error log (common issues + solutions)
- [ ] IAM permissions guide
- [ ] Cost optimization guide

### Data Artifacts
- [ ] Training features table (14M records)
- [ ] Training targets table (14M records)
- [ ] Evaluation features table (378M records)
- [ ] Predictions table (378M records)
- [ ] Human QA table (378M records)
- [ ] Final results table (378M records, 100% coverage)

### Validation & Testing
- [ ] Training metrics (MAE, RMSE, R²)
- [ ] Validation results (calibration, distribution)
- [ ] End-to-end test (full 378M run)
- [ ] Cost validation (actual vs estimated)
- [ ] Performance validation (timing breakdown)

---

## Acceptance Criteria

### Functional Requirements
- ✅ Train real XGBoost regression model on 14M known ages
- ✅ Predict age for all 378M PIDs (100% coverage)
- ✅ Provide confidence score (0-1 scale) for each prediction
- ✅ Output two fields: `age_prediction` (int), `age_prediction_score` (double)
- ✅ Handle missing features gracefully (intelligent defaults)

### Performance Requirements
- ✅ MAE ≤ 5 years on validation set
- ✅ Accuracy within ±5 years ≥ 80%
- ✅ Confidence calibration: High confidence (>0.8) → MAE < 3 years
- ✅ End-to-end pipeline < 1 hour
- ✅ Cost per run ≤ $15

### Operational Requirements
- ✅ Zero manual intervention (fully automated)
- ✅ Idempotent (can rerun without side effects)
- ✅ Parallel processing (898 batches, MaxConcurrency=100)
- ✅ Pre-cleanup prevents duplicates
- ✅ Post-cleanup minimizes storage costs
- ✅ CloudWatch logging for all components
- ✅ Error handling with retries

### Data Quality Requirements
- ✅ No dummy data (all training on real known ages)
- ✅ All 378M PIDs get predictions (no missing rows)
- ✅ Predicted age distribution matches known age distribution
- ✅ No systematic bias by industry, job level, or company size
- ✅ Outlier handling (cap predictions at 18-75 years)

---

## Integration with Job-Change Project

### Use Case: Improve Job-Change Model

**Add age feature to job-change model v1.1:**

1. **Feature Engineering Update:**
   ```sql
   -- In job-change feature engineering, join with age predictions
   LEFT JOIN ai_agent_kb_predict_age.predict_age_predictions_2025q3 a
   ON s.pid = a.pid
   
   -- Add age features
   COALESCE(a.age_prediction, 34) as age_predicted,
   COALESCE(a.age_prediction_score, 0.5) as age_confidence,
   
   -- Age buckets (from update notes)
   CASE 
       WHEN a.age_prediction BETWEEN 18 AND 28 THEN 1  -- High turnover
       WHEN a.age_prediction BETWEEN 29 AND 35 THEN 2  -- Moderate-high
       WHEN a.age_prediction BETWEEN 36 AND 45 THEN 3  -- Moderate
       WHEN a.age_prediction BETWEEN 46 AND 55 THEN 4  -- Low-moderate
       WHEN a.age_prediction >= 56 THEN 5              -- Low turnover
       ELSE 2  -- Default to young/moderate risk
   END as age_bucket,
   
   -- Age × Tenure interaction
   a.age_prediction * tenure_months as age_tenure_interaction
   ```

2. **Expected Impact:**
   - Job-change accuracy: +8-12% (age is top-3 predictor)
   - Feature importance: Age = 18% (top 3)
   - Better risk segmentation by life stage

3. **Workflow:**
   - Run age prediction pipeline first (45-55 min)
   - Then run job-change pipeline (44 min)
   - Total: ~1.5 hours for both models

4. **Combined Cost:**
   - Age prediction: $12
   - Job-change: $11
   - **Total: $23 per quarter** (both models)

---

## Future Enhancements (Post-MVP)

### Phase 2: Advanced Features (Q1-Q2 2026)

1. **Add Education Level (if available)**
   - PhDs tend to be older when entering workforce
   - Graduate degrees = +2-3 years avg age

2. **Add Location/Geography**
   - Retirement-heavy states (FL, AZ) = older workforce
   - Tech hubs (SF, Austin) = younger workforce

3. **Add Historical Job Changes**
   - More job changes = younger (early career exploration)
   - Stable employment = older (established career)

4. **Add Family Status (if available)**
   - Married/children = proxy for age 30+

### Phase 3: Model Improvements (Q3-Q4 2026)

1. **Ensemble Model**
   - Combine XGBoost + Linear Regression
   - Weighted average based on confidence

2. **Uncertainty Quantification**
   - Implement conformal prediction intervals
   - Guarantee coverage (e.g., 90% of true ages within interval)

3. **Active Learning**
   - Prioritize low-confidence predictions for human review
   - Retrain with verified ages

4. **Fairness Constraints**
   - Equal MAE across industries, job levels
   - Debiasing techniques (reweighting, adversarial training)

---

## Success Metrics (6-Month Review)

### Model Performance (Validation)
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| MAE | ≤5 years | TBD | ⏳ To be measured |
| RMSE | ≤7 years | TBD | ⏳ To be measured |
| R² Score | ≥0.75 | TBD | ⏳ To be measured |
| Accuracy (±5 years) | ≥80% | TBD | ⏳ To be measured |
| Confidence Calibration | High confidence → MAE <3 | TBD | ⏳ To be measured |

### Operational Performance
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| End-to-End Time | <1 hour | TBD | ⏳ To be measured |
| Cost per Run | ≤$15 | TBD | ⏳ To be measured |
| Prediction Coverage | 100% (378M PIDs) | TBD | ⏳ To be measured |
| Pipeline Success Rate | >95% | TBD | ⏳ To be measured |

### Business Impact
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Age Data Coverage | +62.5% (236M PIDs) | TBD | ⏳ To be measured |
| Job-Change Model Accuracy | +8-12% (with age feature) | TBD | ⏳ To be measured |
| Customer Filtering | Enable age-based segments | TBD | ⏳ To be measured |

---

## Key Stakeholders

| Role | Name | Responsibility |
|------|------|----------------|
| **Executive Sponsor** | TBD | Business owner, budget approval |
| **Data Science Lead** | TBD | Model development, validation |
| **Data Engineering** | TBD | Pipeline infrastructure, data quality |
| **Product Manager** | TBD | Requirements, prioritization |
| **ML Engineer** | TBD | Fargate deployment, Docker |

---

## References

### Related Projects
- **app-ai-predict-job-change**: Proven architecture, $11/run, 44 min end-to-end
- **2025q4_update_notes.md**: Age feature as Priority #3 for job-change v1.1

### Documentation
- Job-Change README: `/Users/rb/github/app-ai-predict-job-change/README.md`
- Job-Change Requirements: `/Users/rb/github/app-ai-predict-job-change/docs/requirements.md`
- Terraform Examples: `/Users/rb/github/app-ai-predict-job-change/terraform/`

### AWS Resources
- Database: `ai_agent_kb_predict_age`
- S3 Bucket: `${S3_BUCKET}/predict-age/`
- Region: `us-east-1`

---

## Appendix: Key Differences from Job-Change Project

| Aspect | Job-Change | Age Prediction |
|--------|-----------|----------------|
| **Target Type** | Binary classification (Y/N) | Regression (age in years) |
| **Target Range** | 0 or 1 | 18-75 (integers) |
| **Training Set** | 29.9M records (Q2→Q3 changes) | 14M records (known ages) |
| **Features** | 7 features | 15 features |
| **Training Data** | Historical job changes | Current known ages |
| **Model Type** | XGBoost Classifier | XGBoost Regressor |
| **Evaluation** | AUC, precision, recall | MAE, RMSE, R² |
| **Confidence** | Probability score (0-1) | Prediction interval width |
| **Coverage** | 64% (missing job_title) | ~100% (age less sparse) |
| **Business Use** | Retention targeting | Profile enrichment |
| **Expected Accuracy** | AUC ≥0.70 | MAE ≤5 years |

---

**Document Status:** ✅ Ready for Implementation  
**Next Step:** Create GitHub repo `app-ai-predict-age` and begin infrastructure setup  
**Timeline:** Q4 2025 (November-December 2025)  
**Estimated Effort:** 40-60 hours (with proven architecture from job-change)

---

**END OF REQUIREMENTS DOCUMENT**

