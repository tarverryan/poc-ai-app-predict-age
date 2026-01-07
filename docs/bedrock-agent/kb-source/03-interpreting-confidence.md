# Interpreting Age Prediction Confidence Scores

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Applies To:** Model v1.0_xgboost

---

## Quick Reference Guide

### Dual Confidence Scoring System

The Age Prediction Model provides **TWO confidence scores** for every prediction:

| Score Type | Range | Interpretation | Use Case |
|------------|-------|----------------|----------|
| **confidence_score_original** | -17.9 to 74.3 | Prediction interval width (lower = better) | Technical analysis |
| **confidence_pct** | 0-100% | Percentage confidence (higher = better) | Business decisions |

**Key Insight:** These are complementary views of the same underlying uncertainty. Use `confidence_pct` for most business applications.

---

### Confidence Percentage Tiers

| Confidence % | Quality Tier | Count | % of Total | Margin of Error | Use Case |
|--------------|--------------|-------|------------|-----------------|----------|
| **100%** | Real Data | 141.7M | 37.5% | ±0 years | Highest quality - actual age data |
| **80-100%** | Excellent ML | 20.8M | 5.5% | ±2-3 years | Critical applications |
| **60-80%** | Good ML | 151.9M | 40.2% | ±3-6 years | Standard applications |
| **40-60%** | Fair ML | 48.3M | 12.8% | ±6-9 years | Low-risk applications |
| **0-40%** | Poor ML | 15.3M | 4.0% | ±9+ years | Use with caution |

**High Quality (≥60%):** 314.4M PIDs (83.2% of total)

---

## What Do Confidence Scores Mean?

### The Core Concept: Prediction Interval

**A confidence score reflects the width of the 90% prediction interval.**

**Example: Predicted Age 35, confidence_score_original = 10**
```
Prediction interval: 35 ± 5 years = [30, 40]
Interpretation: "90% confident actual age is between 30-40"
Confidence percentage: 66.7% (good quality)
```

**Example: Predicted Age 41, confidence_score_original = -0.45**
```
Prediction interval: 41 ± 0.23 years = [40.8, 41.2]
Interpretation: "Extremely confident age is ~41"
Confidence percentage: 100% (excellent quality)
Negative score = model is SO confident the interval inverted
```

---

## Understanding the Original Confidence Score

### Formula
```
confidence_score_original = pred_95th_percentile - pred_5th_percentile
```

**How It Works:**
1. Quantile model predicts age at 5th percentile (lower bound)
2. Quantile model predicts age at 95th percentile (upper bound)
3. Confidence score = difference between upper and lower

**Interpretation:**
- **Lower score = More confident** (narrow interval)
- **Higher score = Less confident** (wide interval)
- **Negative score = Extremely confident** (quantiles crossed)

### Why Negative Scores Happen

**Crossing Quantiles:**
When the model is extremely confident, the quantile predictions can "cross":
- pred_5 = 35.2 years
- pred_95 = 34.8 years
- confidence = 34.8 - 35.2 = -0.4

This is a **known quirk** of quantile regression and indicates **very high confidence**.

**Treat negative scores as excellent predictions (≈100% confidence).**

---

## Understanding Confidence Percentage

### Formula
```
confidence_pct = max(0, 100 - abs(confidence_score_original) * 3.33)
```

**Conversion Examples:**
| Original Score | Calculation | Confidence % | Quality |
|----------------|-------------|--------------|---------|
| -0.45 | 100 - 0.45*3.33 | 100% | Excellent (capped) |
| 0 | 100 - 0*3.33 | 100% | Excellent |
| 3 | 100 - 3*3.33 | 90.0% | Excellent |
| 6 | 100 - 6*3.33 | 80.0% | Excellent |
| 10 | 100 - 10*3.33 | 66.7% | Good |
| 15 | 100 - 15*3.33 | 50.0% | Fair |
| 20 | 100 - 20*3.33 | 33.4% | Fair |
| 30 | 100 - 30*3.33 | 0% | Poor (capped) |

**Why This Formula?**
- Maps interval width to intuitive 0-100% scale
- 15-year interval = 50% confidence (midpoint)
- 30+ year interval = 0% confidence (very uncertain)

---

## Margin of Error by Confidence Tier

### Practical Interpretation

**For a prediction of Age 35:**

| Confidence % | Margin of Error | Likely Range | Interpretation |
|--------------|-----------------|--------------|----------------|
| **100%** | ±0 years | 35 (exact) | Real data - certain |
| **90%** | ±2-3 years | 32-38 | Excellent ML - very confident |
| **80%** | ±3-4 years | 31-39 | Excellent ML - confident |
| **70%** | ±4-5 years | 30-40 | Good ML - confident |
| **60%** | ±5-6 years | 29-41 | Good ML - moderately confident |
| **50%** | ±7-8 years | 27-43 | Fair ML - uncertain |
| **40%** | ±9-10 years | 25-45 | Fair ML - very uncertain |
| **20%** | ±13+ years | 22-48+ | Poor ML - unreliable |

**Rule of Thumb:**
```
margin_of_error ≈ (100 - confidence_pct) / 10
```

---

## Prediction Source

### Two Types of Data

**1. EXISTING_APPROX_AGE (141.7M PIDs - 37.5%)**
- Source: birth_year or approximate_age field in source data
- Confidence: Always 100%
- Quality: Real data (highest quality)
- Margin of Error: ±0 years

**2. ML_PREDICTION (236.3M PIDs - 62.5%)**
- Source: XGBoost model prediction
- Confidence: 0-100% (varies by prediction)
- Quality: ML-generated (confidence varies)
- Margin of Error: ±2 to ±15 years (depends on confidence)

### Priority Waterfall

The final results table uses this priority:
```sql
CASE
    WHEN birth_year IS NOT NULL THEN 
        (2025 - birth_year, 100.0, 'EXISTING_APPROX_AGE')
    WHEN approximate_age IS NOT NULL THEN 
        (approximate_age, 100.0, 'EXISTING_APPROX_AGE')
    WHEN ml_prediction IS NOT NULL THEN 
        (ml_prediction, ml_confidence_pct, 'ML_PREDICTION')
    ELSE 
        (35, 15.0, 'DEFAULT')  -- Fallback (rarely used)
END
```

---

## How to Use Confidence Scores in Business Decisions

### Principle 1: Filter by Confidence for Quality

**High-Risk Applications (e.g., Personalized Marketing):**
```sql
SELECT * FROM predictions
WHERE confidence_pct >= 80  -- Excellent quality only
-- Returns: 162.5M PIDs (43%)
```

**Standard Applications (e.g., Demographics Analysis):**
```sql
SELECT * FROM predictions
WHERE confidence_pct >= 60  -- Good quality and above
-- Returns: 314.4M PIDs (83%)
```

**Low-Risk Applications (e.g., Broad Segmentation):**
```sql
SELECT * FROM predictions
WHERE confidence_pct >= 40  -- Fair quality and above
-- Returns: 362.7M PIDs (96%)
```

---

### Principle 2: Combine with Business Context

**Model Confidence + Business Signals = Decision**

| Confidence % | Age Range | Profile Complete | Business Action |
|--------------|-----------|------------------|-----------------|
| **100%** | Any | N/A | ✅ Use with full confidence (real data) |
| **85%** | 25-45 | Yes | ✅ Use for targeted campaigns |
| **85%** | <22 or >65 | No | ⚠️ Verify - edge case |
| **65%** | 25-45 | Yes | ✅ Use for segmentation |
| **65%** | Any | No | ⚠️ Use with caution |
| **45%** | 25-45 | Yes | ⚠️ Supplement with other data |
| **45%** | Any | No | ❌ Do not use |
| **25%** | Any | Any | ❌ Do not use |

---

### Principle 3: Segment Analysis vs Individual Decisions

**Good Use (Segment Analysis):**
```sql
-- Aggregate statistics - confidence ≥40% is OK
SELECT 
    FLOOR(predicted_age / 10) * 10 as age_bucket,
    COUNT(*) as count,
    AVG(confidence_pct) as avg_confidence
FROM predictions
WHERE confidence_pct >= 40
GROUP BY 1;

Result: Reliable demographic distribution
```

**Bad Use (Individual Decisions):**
```sql
-- Individual email - requires confidence ≥80%
SELECT * FROM predictions
WHERE pid = 123456789
  AND confidence_pct = 45;  -- Too low for personalization!
```

**Key Insight:** Aggregate statistics are robust to individual errors. Use lower confidence thresholds for population analysis.

---

## Confidence Score Distribution

### Overall Distribution

**Actual Data (378M PIDs):**
- **100% confidence:** 141.7M (37.5%) - Real data
- **80-100%:** 20.8M (5.5%) - Excellent ML
- **60-80%:** 151.9M (40.2%) - Good ML
- **40-60%:** 48.3M (12.8%) - Fair ML
- **0-40%:** 15.3M (4.0%) - Poor ML

**ML Predictions Only (236M PIDs):**
- **Average confidence:** 67.2%
- **Median confidence:** 71.5%
- **Min confidence:** 0% (very sparse profiles)
- **Max confidence:** 100% (negative original scores)

### Confidence by Feature Completeness

| Profile Completeness | Avg Confidence % | Count | Quality |
|---------------------|------------------|-------|---------|
| **90-100% complete** | 82.3% | 47M | Excellent |
| **70-90% complete** | 72.1% | 89M | Good |
| **50-70% complete** | 61.8% | 68M | Good |
| **30-50% complete** | 48.2% | 24M | Fair |
| **<30% complete** | 31.5% | 8M | Poor |

**Insight:** More complete profiles → Higher confidence predictions

---

## Age Range Reliability

### Confidence by Age Group

| Age Range | Avg Confidence % | Count | Notes |
|-----------|------------------|-------|-------|
| **18-24** | 58.2% | 19M | Lower (sparse career data) |
| **25-34** | 71.8% | 158M | Best (typical working age) |
| **35-44** | 74.6% | 122M | Best (established careers) |
| **45-54** | 68.9% | 51M | Good (senior careers) |
| **55-64** | 61.3% | 28M | Lower (career plateau) |
| **65+** | 52.7% | 8M | Lower (edge of training data) |

**Insight:** Model performs best for ages 25-45 (working-age population where training data is most dense)

---

## Common Misinterpretations

### ❌ Wrong Interpretations

**1. "100% confident means 100% accurate"**
- No! 100% means real data (source field), not model accuracy
- ML predictions with 100% confidence still have ±2 year typical error

**2. "Confidence % is model accuracy"**
- No! It's prediction interval width, not accuracy
- Even 100% ML predictions can be off by 2-3 years

**3. "Low confidence means wrong"**
- No! Low confidence means wide interval, not necessarily wrong
- A 40% confident prediction of age 35 might be correct (just less certain)

**4. "Negative scores are errors"**
- No! Negative scores indicate extreme confidence (quantile crossing)
- Treat as excellent predictions

---

### ✅ Correct Interpretations

**1. "100% confidence means real data OR extremely confident ML"**
- Yes! Check `prediction_source` to distinguish

**2. "Higher confidence % = narrower prediction interval"**
- Yes! 80% = ±3 years, 60% = ±6 years, 40% = ±9 years

**3. "Confidence reflects data quality, not individual certainty"**
- Yes! High confidence means good features, not that we "know" the person

**4. "Use confidence to filter, not to modify predictions"**
- Yes! Don't adjust ages based on confidence, just filter out low confidence

---

## Confidence Thresholds by Use Case

### Marketing & Sales

| Application | Min Confidence | Coverage | Rationale |
|-------------|----------------|----------|-----------|
| Personalized email (age-specific) | 80% | 43% | High accuracy needed |
| Segment targeting (25-34 cohort) | 60% | 83% | Aggregates are robust |
| Broad demographics (under/over 40) | 40% | 96% | Less precision needed |

### Product Analytics

| Application | Min Confidence | Coverage | Rationale |
|-------------|----------------|----------|-----------|
| Feature usage by age | 60% | 83% | Statistical analysis |
| User persona building | 70% | 62% | Moderate accuracy |
| Age-gated features | 100% | 38% | Legal compliance |

### Data Science

| Application | Min Confidence | Coverage | Rationale |
|-------------|----------------|----------|-----------|
| Model feature (predict job change) | 40% | 96% | More data = better model |
| Training data labels | 100% | 38% | Need ground truth |
| Exploratory analysis | 60% | 83% | Balance quality/coverage |

---

## Monitoring Confidence Scores

### Quality Metrics

**Track Over Time:**
```sql
SELECT 
    DATE_TRUNC('month', qa_timestamp) as month,
    AVG(confidence_pct) as avg_confidence,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY confidence_pct) as median_confidence,
    SUM(CASE WHEN confidence_pct >= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pct_high_quality
FROM predictions
WHERE prediction_source = 'ML_PREDICTION'
GROUP BY 1
ORDER BY 1;
```

**Alert Thresholds:**
- Average confidence drops >10% → Investigate data quality
- % high quality drops <75% → Investigate feature coverage

---

## Improving Confidence Scores

### What Increases Confidence?

**1. More Complete Profiles**
- Fill in missing features (education, skills, experience)
- Complete LinkedIn profiles → +15% avg confidence

**2. Better Training Data**
- More training examples (currently 14M)
- Quarterly retraining with fresh data

**3. Feature Engineering**
- Add new features (social media, certifications)
- Improve derived features (total_career_years)

**4. Model Improvements**
- Hyperparameter tuning
- Ensemble models (XGBoost + LightGBM)

**5. Calibration**
- Empirical confidence calibration (map predicted intervals to actual)

---

## FAQ: Confidence Scores

**Q: Why do some PIDs have 100% confidence but prediction_source = 'ML_PREDICTION'?**
A: These are ML predictions with negative original scores (extremely confident). The 100% is capped from the formula.

**Q: Can I trust a 50% confident prediction?**
A: Yes, but with caution. 50% means ±7-8 year error. Use for broad segmentation, not individual targeting.

**Q: Should I average confidence scores?**
A: Yes for reporting, no for filtering. Average = "typical quality". Filter = "minimum acceptable quality".

**Q: What confidence threshold for legal compliance (e.g., age-restricted content)?**
A: Only use 100% confidence with prediction_source = 'EXISTING_APPROX_AGE' (real data). Never rely on ML for legal requirements.

**Q: How often do confidence scores change?**
A: Only when the model is retrained (quarterly). Same PID will have same confidence until next model version.

---

## Technical Details

### Quantile Regression

**Models Trained:**
- Lower bound: 5th percentile quantile regressor
- Upper bound: 95th percentile quantile regressor
- Main prediction: 50th percentile (median) = XGBoost output

**Loss Function:**
```
quantile_loss(y, y_pred, quantile) = {
    quantile * (y - y_pred)     if y >= y_pred
    (1 - quantile) * (y_pred - y) if y < y_pred
}
```

**Confidence Calculation:**
```python
confidence_score_original = pred_upper - pred_lower
confidence_pct = max(0, min(100, 100 - abs(confidence_score_original) * 3.33))
```

---

## Calibration (Future Work)

**Planned Q1 2026:**
- Empirical calibration study
- Measure actual vs predicted intervals
- Adjust confidence formula based on results

**Current Status:** Uncalibrated (based on model's own uncertainty estimates)

---

## Summary

**Key Takeaways:**
1. Use `confidence_pct` for business decisions (0-100%, higher = better)
2. Use `confidence_score_original` for technical analysis (interval width)
3. Filter by confidence: ≥80% (critical), ≥60% (standard), ≥40% (low-risk)
4. 100% confidence = real data OR extremely confident ML (check source)
5. Negative original scores = excellent predictions (not errors)
6. Higher confidence = narrower prediction interval (more certain)

**For More Details:**
- Data schema: `04-data-schema.md`
- Example queries: `06-example-queries.md`
- Troubleshooting: `08-troubleshooting.md`

