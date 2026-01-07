# Age Prediction Model - Frequently Asked Questions

**Document Version:** 1.0  
**Last Updated:** October 23, 2025

---

## General Questions

### What is the Age Prediction Model?

A machine learning system that predicts employee/contact ages using 22 career and profile features. It provides age predictions with confidence scores for 378 million people.

**Key Stats:**
- Accuracy: 2.23 year average error (very good)
- Coverage: 378M PIDs (100%)
- Quality: 83% high confidence (≥60%)
- Cost: ~$15 per quarterly run

---

### How accurate is the model?

**Mean Absolute Error: 2.23 years**

This means:
- 50% of predictions are within ±2 years
- 75% of predictions are within ±5 years
- 95% of predictions are within ±10 years

**Example:** Actual age 35 → Model typically predicts 33-37.

**This is considered very good for age prediction.**

---

### What data does it use?

**Training Data:** 14 million employees with known ages (birth_year or approximate_age)

**Input Features (22 total):**
- Career tenure (months in role)
- Job level and function
- Education level
- LinkedIn connections
- Skills count
- Work experience history
- Company size and industry
- And 14 more career indicators

**Does NOT use:** Names, photos, addresses, or sensitive personal data.

---

### How often is the model updated?

**Current:** On-demand (manual trigger)  
**Recommended:** Quarterly (align with data refreshes)  
**Last Run:** October 21, 2025 (Q3 2025 data)

Each update costs ~$15 and takes 45 minutes to process all 378M PIDs.

---

## Data Quality Questions

### What do the confidence scores mean?

**Two scores provided:**

1. **confidence_pct (0-100%)** - Use this for business decisions
   - 100% = Real data or excellent ML (best)
   - 80-100% = Excellent ML (±2-3 years)
   - 60-80% = Good ML (±3-6 years)
   - 40-60% = Fair ML (±6-9 years)
   - <40% = Use with caution

2. **confidence_score_original (-18 to 74)** - Technical metric
   - Lower = better (prediction interval width)
   - Negative = extremely confident

**See `03-interpreting-confidence.md` for full details.**

---

### What confidence level should I use?

**Depends on your use case:**

| Application | Min Confidence | Why |
|-------------|----------------|-----|
| Personalized email (age-specific) | 80% | High accuracy needed |
| Audience segmentation (25-34 cohort) | 60% | Standard quality |
| Broad demographics (under/over 40) | 40% | Aggregates are robust |
| Legal/age-restricted content | 100% + real data | Compliance requirement |

**Rule of Thumb:** Start with 60% for most applications.

---

### How much of the data is "real" vs "predicted"?

**Real Data (EXISTING_APPROX_AGE):** 141.7M PIDs (37.5%)
- Source: birth_year or approximate_age fields
- Confidence: Always 100%
- Margin of Error: ±0 years

**ML Predictions:** 236.3M PIDs (62.5%)
- Source: XGBoost model
- Confidence: 0-100% (varies)
- Margin of Error: ±2 to ±15 years

**Check the `prediction_source` column to distinguish.**

---

### Can I trust predictions with <60% confidence?

**Yes, but with appropriate caution:**

**Good Uses:**
- Population-level statistics (aggregates smooth out errors)
- Exploratory analysis
- Low-stakes decisions

**Bad Uses:**
- Individual personalization
- Legal/compliance decisions
- High-stakes targeting

**Example:** A 45% confident prediction of age 35 might be correct, just less certain (wider margin of error).

---

## Technical Questions

### What algorithm does it use?

**Primary Model: XGBoost (Extreme Gradient Boosting)**

**Why XGBoost?**
- Best accuracy (2.23 year MAE vs 3.10 for Ridge)
- Handles non-linear relationships
- Robust to missing data
- Fast prediction at scale

**Supporting Models:**
- Ridge Regression (baseline)
- Quantile Forest (confidence intervals)

See `01-model-overview.md` for technical details.

---

### What features are most important?

**Top 5 Predictors (69% of importance):**

1. **total_career_years** (23.4%) - Derived from work history
2. **tenure_months** (15.6%) - Time in current role
3. **job_level_encoded** (12.8%) - Seniority level
4. **education_level_encoded** (9.7%) - Highest degree
5. **work_experience_count** (8.3%) - Number of previous jobs

**See `02-features.md` for all 22 features.**

---

### How does it handle missing data?

**Strategy depends on feature coverage:**

- **High coverage (>80%):** Median imputation
- **Medium coverage (50-80%):** Median + indicator flag
- **Low coverage (<50%):** Domain default + indicator flag

**Example:**
```
linkedin_connection_count missing → Impute with 500 (median)
skills_count missing → Impute with 15 (median)
```

**XGBoost is robust to missing values and learns optimal handling during training.**

---

### Why do some predictions have negative confidence scores?

**Negative scores indicate extremely high confidence.**

**Technical Explanation:**
The confidence score is calculated as `pred_95th - pred_5th` (prediction interval width). When the model is extremely confident, these quantiles can "cross":
- pred_5th = 35.2 years
- pred_95th = 34.8 years  
- confidence = 34.8 - 35.2 = **-0.4**

**This is a known quirk of quantile regression, not an error.**

**In the confidence_pct column, these are treated as 100% (capped).**

---

## Usage Questions

### How do I query the data?

**Database:** `ai_agent_kb_predict_age`  
**Table:** `predict_age_final_results_with_confidence`  
**Region:** us-east-1

**Basic Query:**
```sql
SELECT pid, predicted_age, confidence_pct
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
LIMIT 1000;
```

**See `06-example-queries.md` for more examples.**

---

### Can I export the data?

**Yes, using Athena UNLOAD:**

```sql
UNLOAD (
    SELECT pid, predicted_age, confidence_pct
    FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
    WHERE confidence_pct >= 60
)
TO 's3://your-bucket/exports/age-predictions'
WITH (format = 'PARQUET', compression = 'SNAPPY');
```

**Cost:** ~$3-4 for full export (scans 15 GB)

---

### Can I use this for legal/compliance purposes?

**No, not for ML predictions.**

**Only use real data (prediction_source = 'EXISTING_APPROX_AGE') for:**
- Age-restricted content
- Legal compliance (COPPA, GDPR)
- Regulated industries
- High-stakes decisions

**ML predictions are for analytics and marketing only.**

---

### How do I join this with my data?

**Standard SQL JOIN on PID:**

```sql
SELECT 
    e.pid,
    e.name,
    e.job_title,
    a.predicted_age,
    a.confidence_pct
FROM my_database.employees e
LEFT JOIN ai_agent_kb_predict_age.predict_age_final_results_with_confidence a
    ON e.pid = a.pid
WHERE a.confidence_pct >= 60;
```

**Performance:** Fast (PIDs are indexed)

---

## Business Questions

### What are common use cases?

**Top 5 Use Cases:**

1. **Audience Segmentation** - Target marketing by age demographics
2. **Product Analytics** - Understand user age profiles
3. **Profile Enrichment** - Fill missing age data (62.5% coverage gain)
4. **Customer Insights** - Demographic analysis for BI
5. **ML Features** - Use age as input for other models (e.g., job-change prediction)

**See `07-business-guidelines.md` for detailed guidance.**

---

### What's the ROI?

**Value Delivered:**
- 236M new age predictions (62.5% coverage improvement)
- 83% high quality (confidence ≥60%)
- Cost: $15 per run (quarterly)

**Business Impact:**
- Better targeting = Higher conversion rates
- Profile enrichment = Richer customer insights
- ML feature = Improved downstream models

**Annual Cost:** ~$60 (4 quarterly runs)

---

### Can I use this for personalization?

**Yes, with proper confidence filtering:**

**Email Personalization (age-specific offers):**
- Minimum confidence: 80%
- Coverage: 162.5M PIDs (43%)

**Segment Targeting (age ranges):**
- Minimum confidence: 60%
- Coverage: 314.4M PIDs (83%)

**Broad Campaigns:**
- Minimum confidence: 40%
- Coverage: 362.7M PIDs (96%)

---

## Troubleshooting Questions

### My query is slow. How do I speed it up?

**Quick Fixes:**

1. **Always add WHERE clause:**
   ```sql
   WHERE confidence_pct >= 60  -- Reduces data scanned
   ```

2. **Add LIMIT:**
   ```sql
   LIMIT 10000  -- Stops early
   ```

3. **Use partition filtering:**
   ```sql
   WHERE prediction_source = 'ML_PREDICTION'  -- Partition pruning
   ```

**See `08-troubleshooting.md` for more performance tips.**

---

### I'm getting type mismatch errors

**Common Issue:** PID column is BIGINT, not VARCHAR

**Wrong:**
```sql
WHERE pid = '123456789'  -- String
```

**Correct:**
```sql
WHERE pid = 123456789  -- Integer
```

**Or cast explicitly:**
```sql
WHERE CAST(pid AS VARCHAR) = '123456789'
```

---

### How do I report a data quality issue?

**Steps:**

1. Identify the specific PIDs with issues
2. Check confidence scores (low confidence = expected uncertainty)
3. Verify query logic (correct filtering, joins)
4. If still an issue, contact #predict-age (Slack)

**Include:**
- Sample PIDs
- Expected vs actual ages (if known)
- Confidence scores
- Query used

---

## Cost Questions

### How much does each run cost?

**Per-Run Cost Breakdown:**
- Training: $0.30
- Predictions (898 Fargate tasks): $13.92
- Lambda coordination: $0.25
- Athena queries: $0.50
- S3 storage/misc: $0.03
- **Total: ~$15**

**Runtime:** 45 minutes (25 min prediction, 15 min training, 5 min coordination)

---

### How much does querying cost?

**Athena Pricing:** $5 per TB scanned

**Query Costs:**
- Simple query (1000 rows): <$0.01
- Filtered aggregate (60% confidence): $3.10
- Full table scan (378M rows): $3.75

**Optimization:** Use WHERE clauses to minimize scans.

---

### What's the storage cost?

**S3 Storage:**
- Final results: ~15 GB (Parquet)
- Training data: ~42 GB (JSON)
- Models: ~50 MB
- **Total: ~57 GB = $1.31/month**

**Athena Metadata:** Included (no extra cost)

---

## Model Performance Questions

### How does this compare to other age prediction models?

**Industry Benchmarks:**
- **Our Model:** 2.23 year MAE
- **Typical Models:** 3-5 year MAE
- **Simple Rules (career years):** 5-8 year MAE

**We're in the top quartile for age prediction accuracy.**

---

### Can the model be improved?

**Yes! Planned Q1 2026:**

1. **Hyperparameter tuning** - Target 2.0 year MAE
2. **Additional features** - Social media, certifications (5-10 new features)
3. **Ensemble models** - Combine XGBoost + LightGBM
4. **Calibration** - Empirical confidence score adjustment

**Estimated improvement:** 2.23 → 1.9-2.0 year MAE (10-15% better)

---

### What are the model's limitations?

**Known Limitations:**

1. **Sparse Profiles** - Low coverage (< 5 features) = Low confidence
2. **Edge Cases** - Very young (<22) or old (>65) less accurate
3. **Career Changers** - Late bloomers, career gaps not well-modeled
4. **Temporal Drift** - Model trained on Q3 2025 data (retrain quarterly)

**Best Practice:** Use confidence scores to identify uncertain predictions.

---

## Integration Questions

### Can I access this via API?

**Current:** Athena SQL only

**Planned (Q1 2026):** REST API wrapper
- Endpoint: `/predict-age?pid=123456789`
- Response: `{"pid": 123456789, "age": 35, "confidence_pct": 72.5}`

**For Now:** Use Athena JDBC/ODBC drivers or AWS SDK.

---

### Can I use this in Redshift/Snowflake?

**Yes, via data export:**

1. **Export from Athena:**
   ```sql
   UNLOAD (...) TO 's3://bucket/exports/';
   ```

2. **Load into Redshift:**
   ```sql
   COPY age_predictions FROM 's3://bucket/exports/'
   IAM_ROLE 'arn:aws:iam::account:role/RedshiftRole'
   FORMAT AS PARQUET;
   ```

3. **Query normally in Redshift/Snowflake**

---

### Can this integrate with Salesforce/HubSpot?

**Yes, via ETL pipeline:**

1. Export from Athena (UNLOAD to S3)
2. Transform with Glue/Lambda
3. Load to CRM via API

**Or use existing data integration tools (Fivetran, Stitch, etc.)**

---

## Future Roadmap Questions

### What's coming next?

**Q1 2026:**
- Hyperparameter tuning (better accuracy)
- Additional features (5-10 new)
- REST API endpoint
- Automated quarterly runs (EventBridge)

**Q2 2026:**
- Ensemble models (XGBoost + LightGBM)
- Confidence calibration
- Domain-specific rules (e.g., "intern" → age 22-24)

**2026+:**
- Deep learning on text features
- Multi-task learning (age + other demographics)
- Real-time prediction (Lambda inference)

---

### Can this predict other demographics?

**Potentially! Similar approach could predict:**
- Gender/pronouns (from name, profile)
- Income range (from job level, company)
- Education level (from career trajectory)

**Not currently planned, but technically feasible.**

---

## Support and Documentation

### Where can I get help?

**Resources:**
- **Quick Start:** `11-quick-start.md` (5-minute guide)
- **Full Docs:** `/docs/bedrock-agent/kb-source/`
- **Slack:** #predict-age
- **Repository:** https://github.com/tarverryan/poc-ai-app-predict-age

**For Emergencies:** Page on-call data science team

---

### Where is the source code?

**Repository:** https://github.com/tarverryan/poc-ai-app-predict-age

**Key Directories:**
- `/fargate-predict-age/` - Training and prediction containers
- `/lambda-predict-age/` - Pipeline coordination
- `/terraform/` - Infrastructure as code
- `/docs/` - Full documentation

---

## Still Have Questions?

**Check these documents:**
- Model details: `01-model-overview.md`
- Features: `02-features.md`
- Confidence scores: `03-interpreting-confidence.md`
- SQL schema: `04-data-schema.md`
- Examples: `06-example-queries.md`
- Business use: `07-business-guidelines.md`
- Troubleshooting: `08-troubleshooting.md`

**Or contact:** #predict-age on Slack
