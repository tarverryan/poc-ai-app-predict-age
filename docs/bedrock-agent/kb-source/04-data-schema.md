# Age Prediction Data Schema and Query Patterns

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Database:** ai_agent_kb_predict_age  
**Region:** us-east-1

---

## Overview

This document provides comprehensive SQL schema documentation and query patterns for the Age Prediction Model data.

**Primary Production Table:**
- `predict_age_final_results_with_confidence` (378M rows)

**Supporting Tables:**
- `predict_age_full_evaluation_raw_378m` (source data)
- `predict_age_training_raw_14m` (training data)
- `predict_age_training_targets_14m` (training targets)

---

## Production Table Schema

### predict_age_final_results_with_confidence

**View Definition:**
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

**Columns:**

| Column | Type | Description | Range/Values |
|--------|------|-------------|--------------|
| `pid` | BIGINT | Unique person identifier | 1000000 - 999999999999 |
| `predicted_age` | INTEGER | Predicted or actual age | 18-75 (typically 25-45) |
| `confidence_score_original` | DOUBLE | Prediction interval width | -17.9 to 74.3 (lower = better) |
| `confidence_pct` | DOUBLE | Confidence percentage | 0-100% (higher = better) |
| `prediction_source` | STRING | Data source | 'EXISTING_APPROX_AGE' or 'ML_PREDICTION' |
| `qa_timestamp` | TIMESTAMP | Generation timestamp | 2025-10-21 (Q3 2025) |

**Indexes:** Partitioned by `prediction_source` for performance

**Storage:** S3 (Parquet format), ~15 GB

---

## Common Query Patterns

### Pattern 1: Basic Filtering by Confidence

```sql
-- Get high-confidence predictions only
SELECT pid, predicted_age, confidence_pct
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
LIMIT 1000;
```

**Use Case:** Standard quality filtering  
**Returns:** 314.4M rows (83%)  
**Runtime:** ~2 seconds  

---

### Pattern 2: Age Range Segmentation

```sql
-- Segment by age range
SELECT 
    CASE 
        WHEN predicted_age < 25 THEN '18-24'
        WHEN predicted_age < 35 THEN '25-34'
        WHEN predicted_age < 45 THEN '35-44'
        WHEN predicted_age < 55 THEN '45-54'
        WHEN predicted_age < 65 THEN '55-64'
        ELSE '65+'
    END as age_bucket,
    COUNT(*) as count,
    ROUND(AVG(confidence_pct), 1) as avg_confidence
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
GROUP BY 1
ORDER BY 1;
```

**Use Case:** Demographics analysis  
**Runtime:** ~15 seconds  
**Returns:** 6 age buckets with counts

---

### Pattern 3: Quality Distribution

```sql
-- Analyze confidence distribution
SELECT 
    CASE 
        WHEN confidence_pct = 100 AND prediction_source = 'EXISTING_APPROX_AGE' THEN 'Real Data'
        WHEN confidence_pct >= 80 THEN 'Excellent ML'
        WHEN confidence_pct >= 60 THEN 'Good ML'
        WHEN confidence_pct >= 40 THEN 'Fair ML'
        ELSE 'Poor ML'
    END as quality_tier,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / 378024173, 1) as pct,
    ROUND(AVG(predicted_age), 1) as avg_age
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
GROUP BY 1
ORDER BY MIN(confidence_pct) DESC;
```

**Use Case:** Data quality assessment  
**Runtime:** ~20 seconds

---

### Pattern 4: Specific PID Lookup

```sql
-- Get prediction for specific person
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    prediction_source,
    CASE 
        WHEN confidence_pct >= 80 THEN 'Use with high confidence'
        WHEN confidence_pct >= 60 THEN 'Use with moderate confidence'
        ELSE 'Use with caution'
    END as recommendation
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE pid = 123456789;
```

**Use Case:** Individual record lookup  
**Runtime:** <1 second (indexed)

---

### Pattern 5: Age Distribution Analysis

```sql
-- Detailed age distribution with statistics
SELECT 
    FLOOR(predicted_age / 10) * 10 as age_decade,
    COUNT(*) as count,
    MIN(predicted_age) as min_age,
    MAX(predicted_age) as max_age,
    ROUND(AVG(confidence_pct), 1) as avg_confidence,
    ROUND(STDDEV(confidence_pct), 1) as stddev_confidence
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
GROUP BY 1
ORDER BY 1;
```

**Use Case:** Population demographics  
**Runtime:** ~15 seconds

---

### Pattern 6: Comparing Real vs ML Predictions

```sql
-- Compare real data vs ML predictions
SELECT 
    prediction_source,
    COUNT(*) as count,
    ROUND(AVG(predicted_age), 1) as avg_age,
    ROUND(AVG(confidence_pct), 1) as avg_confidence,
    MIN(confidence_pct) as min_confidence,
    MAX(confidence_pct) as max_confidence
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
GROUP BY 1;
```

**Use Case:** Data source analysis  
**Runtime:** ~10 seconds

---

### Pattern 7: High-Quality ML Predictions Only

```sql
-- Get only excellent ML predictions (exclude real data)
SELECT pid, predicted_age, confidence_pct
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE prediction_source = 'ML_PREDICTION'
  AND confidence_pct >= 80
LIMIT 1000;
```

**Use Case:** Testing ML quality  
**Returns:** 20.8M rows  
**Runtime:** ~3 seconds

---

### Pattern 8: Random Sample for Validation

```sql
-- Get random sample across all quality tiers
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    prediction_source
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE MOD(pid, 10000) = 42  -- Deterministic sampling
LIMIT 1000;
```

**Use Case:** Quality validation, testing  
**Returns:** ~37,800 rows (1% sample)

---

### Pattern 9: Age with Margin of Error

```sql
-- Show age with confidence interval
SELECT 
    pid,
    predicted_age,
    CAST(predicted_age - (confidence_score_original / 2) AS INTEGER) as age_lower_bound,
    CAST(predicted_age + (confidence_score_original / 2) AS INTEGER) as age_upper_bound,
    confidence_pct,
    '90% likely between ' || 
      CAST(predicted_age - CAST(confidence_score_original/2 AS INTEGER) AS VARCHAR) || 
      ' and ' || 
      CAST(predicted_age + CAST(confidence_score_original/2 AS INTEGER) AS VARCHAR) as interpretation
FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
LIMIT 100;
```

**Use Case:** Showing uncertainty ranges  
**Runtime:** ~2 seconds

---

### Pattern 10: Export to CSV

```sql
-- Export subset for external analysis
UNLOAD (
    SELECT 
        pid,
        predicted_age,
        confidence_pct,
        prediction_source
    FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence
    WHERE confidence_pct >= 60
      AND predicted_age BETWEEN 25 AND 45
)
TO 's3://your-bucket/exports/age-predictions-25-45'
WITH (format = 'PARQUET', compression = 'SNAPPY');
```

**Use Case:** Data export for downstream systems

---

## Performance Optimization

### Best Practices

**1. Always Filter by Confidence First**
```sql
-- Good (filters first)
WHERE confidence_pct >= 60 AND predicted_age BETWEEN 25 AND 35

-- Bad (full scan)
WHERE predicted_age BETWEEN 25 AND 35 AND confidence_pct >= 60
```

**2. Use Partitioning**
```sql
-- Leverage partition pruning
WHERE prediction_source = 'ML_PREDICTION'  -- Partition column
```

**3. Limit Result Sets**
```sql
-- Always use LIMIT for exploratory queries
LIMIT 1000
```

**4. Use Approximate Aggregates for Large Queries**
```sql
-- Use APPROX_DISTINCT for faster counts
SELECT APPROX_DISTINCT(pid) as approx_count
FROM table
WHERE confidence_pct >= 60;
```

---

## Common Athena Errors and Solutions

### Error 1: Query Timeout
**Error:** `Query exhausted resources at this scale factor`

**Solution:** Add WHERE clause to reduce data scanned
```sql
-- Before (scans all 378M rows)
SELECT * FROM predictions;

-- After (scans subset)
SELECT * FROM predictions
WHERE confidence_pct >= 60
LIMIT 10000;
```

---

### Error 2: Type Mismatch
**Error:** `Cannot apply operator: varchar = bigint`

**Solution:** Cast types correctly
```sql
-- Wrong
WHERE pid = '123456789'

-- Correct
WHERE pid = 123456789
-- or
WHERE CAST(pid AS VARCHAR) = '123456789'
```

---

### Error 3: Column Not Found
**Error:** `Column 'confidence_score' cannot be resolved`

**Solution:** Use correct column name
```sql
-- Wrong
SELECT confidence_score

-- Correct  
SELECT confidence_score_original  -- or confidence_pct
```

---

## Integration Examples

### Joining with Other Tables

```sql
-- Join age predictions with employee data
SELECT 
    e.pid,
    e.name,
    e.job_title,
    a.predicted_age,
    a.confidence_pct,
    a.prediction_source
FROM your_database.employees e
LEFT JOIN ai_agent_kb_predict_age.predict_age_final_results_with_confidence a
    ON e.pid = a.pid
WHERE a.confidence_pct >= 60;
```

---

## Cost Estimation

### Query Cost Formula
```
Cost = (Data Scanned in TB) × $5.00
```

**Examples:**
- Full table scan (378M rows): $3.75
- Filtered query (60% confidence): $3.10
- Single PID lookup: $0.0000001

**Best Practice:** Use `WHERE` clauses to minimize data scanned

---

## Additional Tables (Supporting)

### predict_age_full_evaluation_raw_378m
**Purpose:** Source data for predictions  
**Rows:** 378,024,173  
**Columns:** pid, birth_year, approximate_age, profile_json  
**Format:** JSON (row format)

### predict_age_training_raw_14m
**Purpose:** Training data with known ages  
**Rows:** 14,171,296  
**Format:** JSON (row format)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-23 | Initial schema documentation |

---

**For More Examples:** See `06-example-queries.md`  
**For Troubleshooting:** See `08-troubleshooting.md`
