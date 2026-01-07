# Age Prediction Model - Complete Overview

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Model Version:** v1.0_xgboost  
**Production Status:** Deployed and Validated

---

## Executive Summary

This document provides a comprehensive overview of the Age Prediction Model, a machine learning system that predicts employee/contact ages using 22 career and profile features.

**Key Facts:**
- **Training Data:** 14 million employees with known ages (Q3 2025)
- **Algorithm:** XGBoost Gradient Boosting with Ridge and Quantile models
- **Features:** 22 carefully selected career and demographic features
- **Production Scale:** 378 million employees/contacts scored
- **Accuracy:** 2.23 year Mean Absolute Error (very good for age prediction)
- **Update Frequency:** Quarterly (aligns with data availability)

---

## What This Model Does

### Primary Function
Predicts the age of employees and contacts based on their career profile, tenure, job characteristics, and digital footprint.

### Output Format
For each person (identified by PID), the model provides:
1. **Predicted Age:** Integer value (18-75 years, typically 30-45)
2. **Confidence Score (Original):** Prediction interval width (-17.9 to 74.3, lower = better)
3. **Confidence Percentage:** 0-100% scale (higher = better, 100% = real data)
4. **Prediction Source:** "EXISTING_APPROX_AGE" (real data) or "ML_PREDICTION"
5. **Timestamp:** When the prediction was generated
6. **Model Version:** v1.0_xgboost

### Business Use Cases
- **Audience Segmentation:** Target marketing campaigns by age demographics
- **Product Analytics:** Understand user demographics and preferences
- **Profile Enrichment:** Fill missing age data (62.5% coverage improvement)
- **Customer Insights:** Demographic analysis for business intelligence
- **Data Quality:** Distinguish real ages (100% confidence) from predictions
- **Predictive Analytics:** Use age as a feature in other ML models (e.g., job-change prediction)

---

## How the Model Works

### Training Approach: Supervised Learning from Known Ages

**Step 1: Historical Data Collection**
- Source: 378M+ employee/contact profiles from Q3 2025
- Training Sample: 14M employees with known ages (birth_year or approximate_age fields)
- Evaluation Set: 378M total PIDs (236M need predictions, 142M have real ages)

**Step 2: Ground Truth (Known Ages)**
The model learns from PIDs where age is known:
```sql
actual_age = CASE 
    WHEN birth_year IS NOT NULL THEN 2025 - birth_year
    WHEN approximate_age IS NOT NULL THEN approximate_age
    ELSE NULL  -- No ground truth, need ML prediction
END
```

**Step 3: Feature Engineering**
For each employee/contact, calculate 22 predictive features:
1. Career tenure (months in current role)
2. LinkedIn connection count
3. Company size (encoded)
4. Job level/seniority (encoded)
5. Industry type
6. Education level (from LinkedIn profile)
7. Skills count (proxy for experience)
8. Work experience count (number of jobs)
9. Total career years (strongest predictor)
10. Profile completeness
... and 12 more career indicators

**Step 4: Model Training (XGBoost)**
- Algorithm: Gradient Boosted Decision Trees (XGBoost)
- Training Set: 1M sample from 14M (for speed)
- Validation Set: Held-out 20%
- Regularization: L1 and L2 to prevent overfitting
- Hyperparameters: Default XGBoost settings (opportunity for tuning)

**Step 5: Pattern Learning**
The model learns complex patterns like:
- "17 years total career + Manager level + Tech industry → Age ~42"
- "2 years tenure + Entry level + 500 LinkedIn connections → Age ~26"
- "PhD education + Senior level + 15 years experience → Age ~41"

These patterns are **discovered empirically from data**, not pre-defined rules.

**Step 6: Prediction Generation**
For employees without age data:
- Extract same 22 features
- Run through trained XGBoost model
- Model outputs predicted age
- Quantile regression provides confidence interval
- Save prediction + confidence scores

---

## Model Type and Architecture

### Algorithm: XGBoost (Extreme Gradient Boosting)

**Why XGBoost?**
- Handles non-linear relationships (age doesn't scale linearly with features)
- Robust to missing data (many PIDs have incomplete profiles)
- Fast prediction (critical for 236M predictions)
- High accuracy (best-in-class for tabular data)
- Feature importance (understand what drives predictions)

**Model Comparison:**

| Model | MAE (years) | R² Score | Status |
|-------|-------------|----------|--------|
| Ridge Regression | 3.10 | 0.665 | Baseline |
| **XGBoost** | **2.23** | **0.739** | **Production** |
| Quantile Forest | 2.53 | 0.710 | Confidence intervals |

**Winner:** XGBoost (28% better than Ridge baseline)

### Three-Model Ensemble

The pipeline trains three complementary models:

**1. Ridge Regression (Baseline)**
- Linear model with L2 regularization
- Fast training (~1 minute)
- Interpretable coefficients
- Performance: 3.10 year MAE
- Use: Benchmark comparison

**2. XGBoost Regressor (Primary)**
- 200 decision trees (default)
- Gradient boosting
- Non-linear feature interactions
- Performance: 2.23 year MAE ✅
- Use: Main age prediction

**3. Quantile Forest (Confidence)**
- Two models: 5th and 95th percentile
- Prediction interval estimation
- Confidence score = pred_95 - pred_5
- Performance: 2.53 year MAE
- Use: Confidence score calculation

---

## Training Data Details

### Data Source
- **Database:** `ai_agent_kb_predict_age`
- **Raw Data Table:** `predict_age_training_raw_14m`
- **Targets Table:** `predict_age_training_targets_14m`
- **Sample Size:** 14,171,296 PIDs with known ages

### Data Quality
- **Complete Profiles:** ~60% have all 22 features
- **Partial Profiles:** ~30% missing 1-5 features
- **Sparse Profiles:** ~10% missing 6+ features
- **Age Range:** 18-75 years (clipped at extremes)
- **Median Age:** 34 years
- **Most Common:** 30s (working-age population)

### Feature Coverage
- **High Coverage (>90%):** Tenure, job level, company size, industry
- **Medium Coverage (60-90%):** LinkedIn connections, education, skills
- **Low Coverage (<60%):** Social media, certifications, awards

---

## Prediction Generation (Production)

### Scale and Performance
- **Total PIDs:** 378,024,173 (100% coverage)
- **Real Ages:** 141,727,672 (37.5%) - from birth_year/approximate_age
- **ML Predictions:** 236,296,501 (62.5%) - generated by model
- **Parallel Processing:** 898 Fargate tasks (4 vCPU, 16GB each)
- **Runtime:** ~25 minutes for all predictions
- **Cost:** ~$14 per run

### Smart Filtering Strategy
The pipeline only predicts for PIDs **missing age data**:
```sql
WHERE (birth_year IS NULL AND approximate_age IS NULL)
```

This optimization:
- Saves compute cost (no redundant predictions)
- Preserves real data quality (100% confidence)
- Reduces runtime (236M vs 378M predictions)

### Inline JSON Parsing
Predictions are made directly from raw JSON data:
1. Query raw table (378M records, JSON format)
2. Parse JSON inline (extract 22 features)
3. Load models from S3
4. Make predictions
5. Save to S3 (Parquet format)

This approach eliminates the need for a separate parsing step, saving ~$30 per run.

---

## Infrastructure and Deployment

### AWS Architecture
- **Orchestration:** Step Functions (8-stage pipeline)
- **Training:** Fargate container (16 vCPU, 64GB RAM)
- **Prediction:** 898 parallel Fargate containers (4 vCPU, 16GB each)
- **Data Storage:** S3 (raw data, models, predictions)
- **Data Warehouse:** Athena (query interface)
- **Coordination:** 6 Lambda functions

### Pipeline Stages
1. **PreCleanup** - Remove old results
2. **Training** - Train 3 models (~15 min, $0.30)
3. **BatchGenerator** - Create 898 batch IDs
4. **CreatePredictionsTable** - Pre-create Athena table
5. **ParallelPrediction** - 898 tasks predict ages (~25 min, $14)
6. **HumanQA** - Create QA table for review
7. **FinalResults** - Merge real ages + ML predictions
8. **Cleanup** - Remove intermediate data

### Cost Breakdown
- Training: $0.30
- Predictions: $13.92
- Lambda: $0.25
- Athena: $0.50
- S3/misc: $0.03
- **Total:** ~$15 per run

### Update Frequency
- **Current:** On-demand (manual trigger)
- **Recommended:** Quarterly (align with data refreshes)
- **Future:** EventBridge scheduled automation

---

## Model Performance

### Accuracy Metrics

**Mean Absolute Error (MAE): 2.23 years**
- On average, predictions are within ±2.23 years of actual age
- Example: Actual age 35 → Predicted 33-37 (typical)
- **Rating:** Very Good for age prediction

**R² Score: 0.739**
- Model explains 73.9% of age variance
- Remaining 26.1% is inherent noise/individual variation
- **Rating:** Strong predictive power

**Root Mean Square Error (RMSE): 5.05 years**
- Measures larger errors more heavily
- Used for 95% confidence intervals (±10 years)

### Error Distribution
- **Within ±2 years:** ~50% of predictions (excellent)
- **Within ±5 years:** ~75% of predictions (good)
- **Within ±10 years:** ~95% of predictions (acceptable)
- **Beyond ±10 years:** ~5% of predictions (use with caution)

### Confidence Distribution

| Confidence Tier | Count | Percentage | Quality |
|-----------------|-------|------------|---------|
| **Real Data (100%)** | 141.7M | 37.5% | Perfect |
| **Excellent (80-100%)** | 20.8M | 5.5% | Very high |
| **Good (60-80%)** | 151.9M | 40.2% | High |
| **Fair (40-60%)** | 48.3M | 12.8% | Moderate |
| **Poor (<40%)** | 15.3M | 4.0% | Use with caution |

**High Quality (≥60%):** 314.4M PIDs (83.2%)

---

## Data Schema

### Production Table
**Table:** `predict_age_final_results_with_confidence`  
**Database:** `ai_agent_kb_predict_age`  
**Region:** us-east-1

**Columns:**
- `pid` (BIGINT) - Unique person identifier
- `predicted_age` (INTEGER) - Predicted age (18-75)
- `confidence_score_original` (DOUBLE) - Interval width (lower = better)
- `confidence_pct` (DOUBLE) - 0-100% scale (higher = better)
- `prediction_source` (STRING) - "EXISTING_APPROX_AGE" or "ML_PREDICTION"
- `qa_timestamp` (TIMESTAMP) - When prediction was generated

### Example Query
```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    prediction_source
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct >= 60  -- High quality only
LIMIT 1000;
```

---

## Model Limitations

### What the Model Can't Do

**1. Individual Circumstances**
- Model predicts based on population patterns, not individual traits
- Cannot account for: career gaps, late bloomers, career changers

**2. Sparse Profiles**
- PIDs with <5 features have lower accuracy
- Confidence scores reflect this uncertainty

**3. Edge Cases**
- Very young (<22) or very old (>65) predictions less accurate
- Model trained on working-age population (25-55)

**4. Temporal Drift**
- Model trained on Q3 2025 data
- Career patterns change over time
- Recommend quarterly retraining

### Best Practices
- ✅ Use confidence scores to filter (≥60% for most applications)
- ✅ Combine with other signals (job title, tenure)
- ✅ Validate predictions in your specific use case
- ✅ Monitor prediction quality over time
- ❌ Don't treat predictions as ground truth
- ❌ Don't use for age-restricted content without verification
- ❌ Don't ignore low confidence scores

---

## Future Improvements

### Short-Term (Q1 2026)
- Hyperparameter tuning (improve MAE to ~2.0 years)
- Add 5-10 new features (social media activity, certifications)
- Ensemble multiple models (XGBoost + LightGBM)

### Medium-Term (Q2 2026)
- Domain-specific rules (e.g., "intern" → age 22-24)
- Feature interaction modeling
- Calibrate confidence scores empirically

### Long-Term (2026+)
- Deep learning on text features (job titles, company names)
- Time-series features (career progression rate)
- Multi-task learning (predict age + other demographics)

---

## Related Models

### Integration Opportunities
- **Job Change Prediction:** Use predicted age as input feature
- **Salary Estimation:** Age correlates with compensation
- **Promotion Likelihood:** Age + tenure interaction
- **Customer Lifetime Value:** Age-based cohort analysis

---

## Version History

| Version | Date | Model | MAE | Notes |
|---------|------|-------|-----|-------|
| 1.0 | 2025-10-23 | XGBoost | 2.23 | Initial production deployment |

**Next Version (1.1 - Planned Q1 2026):**
- Hyperparameter tuning
- Additional features
- Improved confidence calibration

---

## Contact and Support

**Data Science Team:** #predict-age (Slack)  
**Documentation:** `/docs/bedrock-agent/kb-source/`  
**Repository:** https://github.com/tarverryan/poc-ai-app-predict-age

**For Technical Issues:** See `08-troubleshooting.md`  
**For Business Questions:** See `07-business-guidelines.md`  
**For SQL Help:** See `06-example-queries.md`

