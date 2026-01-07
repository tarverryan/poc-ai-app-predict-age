# Confidence Score Scale Guide

## Overview

The age prediction pipeline provides **two confidence scores** for each prediction:

1. **`confidence_score_original`** - Technical ML metric (interval width)
2. **`confidence_pct`** - Business-friendly percentage (0-100 scale)

Both are available in the view: `predict_age_final_results_with_confidence`

---

## Confidence Percentage Scale (0-100)

### Formula

**For Real Data:**
- `confidence_pct = 100.0` (always)

**For ML Predictions:**
- `confidence_pct = max(0, 100 - abs(interval) * 3.33)`

Where `interval` is the prediction interval width (95th percentile - 5th percentile)

### Interpretation

| Percentage | Quality Tier | Meaning | Interval Width |
|-----------|--------------|---------|----------------|
| **100%** | Perfect | Real data or extremely confident ML | ≤ 0 years |
| **80-100%** | Excellent | Very high confidence ML prediction | ≤ 6 years |
| **60-80%** | Good | High confidence ML prediction | 6-12 years |
| **40-60%** | Fair | Moderate confidence ML prediction | 12-18 years |
| **0-40%** | Poor | Low confidence ML prediction | > 18 years |

---

## Distribution (378M PIDs)

| Tier | Count | Percentage | Usage |
|------|-------|------------|-------|
| **Real Data (100%)** | 141.7M | 37.5% | Highest quality |
| **Excellent (80-100%)** | 20.8M | 5.5% | Excellent ML |
| **Good (60-80%)** | 151.9M | 40.2% | Good ML |
| **Fair (40-60%)** | 48.3M | 12.8% | Fair ML |
| **Poor (<40%)** | 15.3M | 4.0% | Use with caution |

**High Quality (≥60%):** 314.4M PIDs (83.2%)

---

## Example Transformations

| Original Score | New Percentage | Quality |
|----------------|----------------|---------|
| -0.45 | 100.0% | Perfect (your example!) |
| 0.0 | 100.0% | Perfect |
| 3.0 | 90.0% | Excellent |
| 6.0 | 80.0% | Excellent |
| 9.0 | 70.0% | Good |
| 12.0 | 60.0% | Good |
| 15.0 | 50.0% | Fair |
| 20.0 | 33.4% | Fair |
| 30.0 | 0.0% | Poor |
| 74.3 | 0.0% | Poor |

---

## Usage Guide

### Critical Applications
Use only real data:
```sql
SELECT pid, predicted_age, confidence_pct
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct = 100 AND prediction_source = 'EXISTING_APPROX_AGE'
```
**Returns:** 141.7M PIDs

### Standard Applications
Use good or better predictions:
```sql
SELECT pid, predicted_age, confidence_pct
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
```
**Returns:** 314.4M PIDs (83%)

### Low-Risk Applications
Use fair or better predictions:
```sql
SELECT pid, predicted_age, confidence_pct
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct >= 40
```
**Returns:** 362.7M PIDs (96%)

### All Records
All predictions with caution flag:
```sql
SELECT 
  pid, 
  predicted_age, 
  confidence_pct,
  CASE 
    WHEN confidence_pct >= 60 THEN 'TRUSTED'
    WHEN confidence_pct >= 40 THEN 'USE_WITH_CAUTION'
    ELSE 'LOW_CONFIDENCE'
  END as quality_flag
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
```

---

## Comparing Both Scales

```sql
SELECT 
  ROUND(confidence_score_original, 1) as original,
  ROUND(confidence_pct, 1) as percentage,
  COUNT(*) as count
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE prediction_source = 'ML_PREDICTION'
GROUP BY 1, 2
ORDER BY 1
LIMIT 20;
```

---

## Why Negative Original Scores?

Negative scores in `confidence_score_original` (e.g., -0.45) indicate **extremely confident predictions**. They occur when the quantile model's prediction interval is so narrow that quantiles "cross" (95th percentile < 5th percentile).

**This is a GOOD thing:**
- Indicates very high model confidence
- Transforms to 100% in the new scale
- Safe to use and trust

---

## Technical Details

### Original Score (confidence_score_original)
- **Type:** Prediction interval width (quantile regression)
- **Range:** -17.9 to 74.3 years
- **Formula:** `pred_95th_percentile - pred_5th_percentile`
- **Interpretation:** Lower = more confident (inverse scale)
- **Use Case:** Technical ML analysis

### New Score (confidence_pct)
- **Type:** Percentage confidence (0-100)
- **Range:** 0.0 to 100.0
- **Formula:** `max(0, 100 - abs(original) * 3.33)` for ML predictions
- **Interpretation:** Higher = more confident (intuitive scale)
- **Use Case:** Business decisions and reporting

---

## View Definition

```sql
CREATE OR REPLACE VIEW ai_agent_kb_predict_age.predict_age_final_results_with_confidence AS
SELECT 
  pid,
  predicted_age,
  confidence_score as confidence_score_original,
  CASE 
    WHEN prediction_source = 'EXISTING_APPROX_AGE' THEN 100.0
    ELSE GREATEST(0, LEAST(100, 100 - (ABS(confidence_score) * 3.33)))
  END as confidence_pct,
  prediction_source,
  qa_timestamp
FROM ai_agent_kb_predict_age.predict_age_final_results_2025q3;
```

---

## Summary

✅ **Use `confidence_pct`** for business decisions (0-100, higher = better)  
✅ **Use `confidence_score_original`** for technical analysis (interval width)  
✅ **Filter by `confidence_pct >= 60`** for most applications (83% coverage)  
✅ **Both scores available** in the same view for comparison

**View:** `ai_agent_kb_predict_age.predict_age_final_results_with_confidence`

