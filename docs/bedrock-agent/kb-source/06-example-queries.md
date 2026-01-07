# Age Prediction - SQL Query Examples

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Database:** ai_agent_kb_predict_age  
**Table:** predict_age_final_results_with_confidence

---

## Query Template

**All queries use this database:**
```sql
-- Always start with this
USE ai_agent_kb_predict_age;

-- Then query the main table
SELECT ... FROM predict_age_final_results_with_confidence WHERE ...;
```

---

## Basic Queries

### Query 1: Get First 10 High-Quality Predictions

```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    prediction_source
FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
LIMIT 10;
```

**Returns:** 10 rows  
**Runtime:** <1 second  
**Use Case:** Quick data preview

---

### Query 2: Lookup Specific Person

```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    confidence_score_original,
    prediction_source,
    qa_timestamp,
    CASE 
        WHEN confidence_pct >= 80 THEN 'High confidence - use freely'
        WHEN confidence_pct >= 60 THEN 'Good confidence - standard use'
        WHEN confidence_pct >= 40 THEN 'Fair confidence - use with caution'
        ELSE 'Low confidence - verify before use'
    END as recommendation
FROM predict_age_final_results_with_confidence
WHERE pid = 123456789;
```

**Returns:** 1 row  
**Runtime:** <1 second  
**Use Case:** Individual record lookup

---

### Query 3: Get Real Data Only

```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    prediction_source
FROM predict_age_final_results_with_confidence
WHERE prediction_source = 'EXISTING_APPROX_AGE'
LIMIT 1000;
```

**Returns:** 1000 rows (from 141.7M real data PIDs)  
**Runtime:** ~2 seconds  
**Use Case:** Ground truth validation

---

## Segmentation Queries

### Query 4: Age Range Distribution

```sql
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
    ROUND(COUNT(*) * 100.0 / 378024173, 2) as percentage,
    ROUND(AVG(confidence_pct), 1) as avg_confidence,
    MIN(confidence_pct) as min_confidence,
    MAX(confidence_pct) as max_confidence
FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
GROUP BY 1
ORDER BY 1;
```

**Returns:** 6 age buckets with statistics  
**Runtime:** ~15 seconds  
**Use Case:** Demographics analysis, audience segmentation

---

### Query 5: Millennials vs Gen Z vs Gen X

```sql
SELECT 
    CASE 
        WHEN predicted_age >= 18 AND predicted_age <= 27 THEN 'Gen Z (1997-2006)'
        WHEN predicted_age >= 28 AND predicted_age <= 43 THEN 'Millennials (1981-1996)'
        WHEN predicted_age >= 44 AND predicted_age <= 59 THEN 'Gen X (1965-1980)'
        WHEN predicted_age >= 60 THEN 'Boomers (1946-1964)'
        ELSE 'Other'
    END as generation,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM predict_age_final_results_with_confidence WHERE confidence_pct >= 60), 1) as pct
FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
GROUP BY 1
ORDER BY MIN(predicted_age);
```

**Returns:** 4 generations with counts  
**Runtime:** ~20 seconds  
**Use Case:** Generational marketing analysis

---

## Quality Analysis Queries

### Query 6: Confidence Distribution

```sql
SELECT 
    CASE 
        WHEN confidence_pct = 100 AND prediction_source = 'EXISTING_APPROX_AGE' THEN 'Real Data (100%)'
        WHEN confidence_pct >= 90 THEN 'Excellent (90-100%)'
        WHEN confidence_pct >= 80 THEN 'Very Good (80-90%)'
        WHEN confidence_pct >= 70 THEN 'Good (70-80%)'
        WHEN confidence_pct >= 60 THEN 'Moderate (60-70%)'
        WHEN confidence_pct >= 50 THEN 'Fair (50-60%)'
        WHEN confidence_pct >= 40 THEN 'Low (40-50%)'
        ELSE 'Poor (<40%)'
    END as confidence_tier,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / 378024173, 2) as pct,
    ROUND(AVG(predicted_age), 1) as avg_age
FROM predict_age_final_results_with_confidence
GROUP BY 1
ORDER BY MIN(confidence_pct) DESC;
```

**Returns:** 8 confidence tiers  
**Runtime:** ~20 seconds  
**Use Case:** Data quality assessment

---

### Query 7: Real Data vs ML Predictions Comparison

```sql
SELECT 
    prediction_source,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / 378024173, 1) as pct,
    ROUND(AVG(predicted_age), 1) as avg_age,
    ROUND(AVG(confidence_pct), 1) as avg_confidence,
    ROUND(MIN(predicted_age), 0) as min_age,
    ROUND(MAX(predicted_age), 0) as max_age,
    ROUND(STDDEV(predicted_age), 1) as stddev_age
FROM predict_age_final_results_with_confidence
GROUP BY 1;
```

**Returns:** 2 rows (real vs ML)  
**Runtime:** ~15 seconds  
**Use Case:** Data source analysis

---

## Advanced Filtering Queries

### Query 8: High-Confidence Young Professionals (25-35)

```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    prediction_source
FROM predict_age_final_results_with_confidence
WHERE predicted_age BETWEEN 25 AND 35
  AND confidence_pct >= 80
ORDER BY confidence_pct DESC
LIMIT 10000;
```

**Returns:** Up to 10,000 young professionals  
**Runtime:** ~5 seconds  
**Use Case:** Targeted marketing for young professionals

---

### Query 9: Uncertain Predictions Needing Review

```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    confidence_score_original,
    prediction_source,
    ROUND((100 - confidence_pct) / 10, 1) as margin_of_error_years
FROM predict_age_final_results_with_confidence
WHERE prediction_source = 'ML_PREDICTION'
  AND confidence_pct < 40
ORDER BY confidence_pct ASC
LIMIT 1000;
```

**Returns:** 1000 least confident predictions  
**Runtime:** ~3 seconds  
**Use Case:** Quality review, model debugging

---

### Query 10: Excellent ML Predictions Only

```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    confidence_score_original
FROM predict_age_final_results_with_confidence
WHERE prediction_source = 'ML_PREDICTION'
  AND confidence_pct >= 90
ORDER BY confidence_pct DESC
LIMIT 5000;
```

**Returns:** Top 5000 ML predictions  
**Runtime:** ~3 seconds  
**Use Case:** ML model validation

---

## Statistical Analysis Queries

### Query 11: Age Distribution by Decade

```sql
SELECT 
    FLOOR(predicted_age / 10) * 10 as age_decade,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / 378024173, 2) as pct,
    MIN(predicted_age) as min_age,
    MAX(predicted_age) as max_age,
    ROUND(AVG(confidence_pct), 1) as avg_confidence
FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
GROUP BY 1
ORDER BY 1;
```

**Returns:** 6-7 decades  
**Runtime:** ~15 seconds  
**Use Case:** Population pyramid analysis

---

### Query 12: Percentile Analysis

```sql
SELECT 
    APPROX_PERCENTILE(predicted_age, 0.10) as p10_age,
    APPROX_PERCENTILE(predicted_age, 0.25) as p25_age,
    APPROX_PERCENTILE(predicted_age, 0.50) as median_age,
    APPROX_PERCENTILE(predicted_age, 0.75) as p75_age,
    APPROX_PERCENTILE(predicted_age, 0.90) as p90_age,
    APPROX_PERCENTILE(confidence_pct, 0.50) as median_confidence
FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60;
```

**Returns:** 1 row with percentiles  
**Runtime:** ~10 seconds  
**Use Case:** Statistical summary

---

## Export and Sampling Queries

### Query 13: Random Sample for Validation

```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    confidence_score_original,
    prediction_source
FROM predict_age_final_results_with_confidence
WHERE MOD(pid, 10000) = 42  -- Deterministic sampling (0.01%)
  AND confidence_pct >= 60
LIMIT 5000;
```

**Returns:** ~3,780 rows (1% sample)  
**Runtime:** ~5 seconds  
**Use Case:** Testing, validation

---

### Query 14: Export High-Quality Subset

```sql
UNLOAD (
    SELECT 
        pid,
        predicted_age,
        confidence_pct,
        prediction_source,
        qa_timestamp
    FROM predict_age_final_results_with_confidence
    WHERE confidence_pct >= 80
)
TO 's3://your-bucket/exports/age-predictions-high-quality/'
WITH (
    format = 'PARQUET',
    compression = 'SNAPPY',
    partitioned_by = ARRAY['prediction_source']
);
```

**Returns:** 162.5M rows exported  
**Runtime:** ~10 minutes  
**Cost:** ~$3.50  
**Use Case:** Data export for downstream systems

---

## Join Queries

### Query 15: Join with Employee Data (Example)

```sql
-- Assuming you have an employees table
SELECT 
    e.pid,
    e.name,
    e.email,
    e.job_title,
    e.company,
    a.predicted_age,
    a.confidence_pct,
    a.prediction_source,
    CASE 
        WHEN a.predicted_age < 30 THEN 'Early Career'
        WHEN a.predicted_age < 45 THEN 'Mid Career'
        ELSE 'Late Career'
    END as career_stage
FROM your_database.employees e
LEFT JOIN ai_agent_kb_predict_age.predict_age_final_results_with_confidence a
    ON e.pid = a.pid
WHERE a.confidence_pct >= 60
LIMIT 1000;
```

**Runtime:** Depends on employees table size  
**Use Case:** Profile enrichment

---

## Monitoring and Alerting Queries

### Query 16: Data Freshness Check

```sql
SELECT 
    DATE_TRUNC('day', qa_timestamp) as prediction_date,
    COUNT(*) as count,
    ROUND(AVG(confidence_pct), 1) as avg_confidence,
    MIN(qa_timestamp) as earliest,
    MAX(qa_timestamp) as latest
FROM predict_age_final_results_with_confidence
GROUP BY 1
ORDER BY 1 DESC;
```

**Returns:** Predictions by date  
**Runtime:** ~5 seconds  
**Use Case:** Verify data freshness

---

### Query 17: Quality Metrics Dashboard

```sql
SELECT 
    COUNT(*) as total_pids,
    SUM(CASE WHEN confidence_pct >= 60 THEN 1 ELSE 0 END) as high_quality_count,
    ROUND(SUM(CASE WHEN confidence_pct >= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as high_quality_pct,
    ROUND(AVG(predicted_age), 1) as avg_age,
    ROUND(AVG(confidence_pct), 1) as avg_confidence,
    ROUND(STDDEV(predicted_age), 1) as stddev_age,
    ROUND(STDDEV(confidence_pct), 1) as stddev_confidence,
    SUM(CASE WHEN prediction_source = 'EXISTING_APPROX_AGE' THEN 1 ELSE 0 END) as real_data_count,
    SUM(CASE WHEN prediction_source = 'ML_PREDICTION' THEN 1 ELSE 0 END) as ml_prediction_count
FROM predict_age_final_results_with_confidence;
```

**Returns:** 1 row with key metrics  
**Runtime:** ~20 seconds  
**Use Case:** Dashboard KPIs

---

## Performance-Optimized Queries

### Query 18: Fast Count by Partition

```sql
-- Use partition column for faster queries
SELECT 
    prediction_source,
    COUNT(*) as count
FROM predict_age_final_results_with_confidence
GROUP BY 1;
```

**Returns:** 2 rows  
**Runtime:** <5 seconds (partition pruning)  
**Use Case:** Quick counts

---

### Query 19: Approximate Distinct Count (Fast)

```sql
-- Use APPROX_DISTINCT for faster counts
SELECT 
    APPROX_DISTINCT(pid) as approx_unique_pids,
    APPROX_PERCENTILE(predicted_age, 0.50) as approx_median_age,
    APPROX_PERCENTILE(confidence_pct, 0.50) as approx_median_confidence
FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60;
```

**Returns:** 1 row  
**Runtime:** ~5 seconds (much faster than exact COUNT DISTINCT)  
**Use Case:** Quick estimates

---

## Business Use Case Queries

### Query 20: Target Audience for Age 30-40 Campaign

```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct
FROM predict_age_final_results_with_confidence
WHERE predicted_age BETWEEN 30 AND 40
  AND confidence_pct >= 70
ORDER BY confidence_pct DESC
LIMIT 50000;
```

**Returns:** Up to 50K target PIDs  
**Runtime:** ~5 seconds  
**Use Case:** Marketing campaign targeting

---

### Query 21: Age Outliers for Review

```sql
-- Find potentially incorrect predictions (very young or very old)
SELECT 
    pid,
    predicted_age,
    confidence_pct,
    prediction_source
FROM predict_age_final_results_with_confidence
WHERE (predicted_age < 20 OR predicted_age > 70)
  AND prediction_source = 'ML_PREDICTION'
ORDER BY predicted_age
LIMIT 1000;
```

**Returns:** Up to 1000 edge cases  
**Runtime:** ~3 seconds  
**Use Case:** Quality review

---

## Cost-Efficient Query Patterns

### Best Practice: Always Filter First

```sql
-- Good: Filter early (scans less data)
SELECT pid, predicted_age
FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60  -- Reduces scan
  AND predicted_age BETWEEN 25 AND 45
LIMIT 10000;

-- Bad: No filtering (scans all 378M rows)
SELECT pid, predicted_age
FROM predict_age_final_results_with_confidence
LIMIT 10000;
```

**Cost Difference:** ~$3 saved per query

---

### Best Practice: Use LIMIT

```sql
-- Always add LIMIT for exploratory queries
SELECT * FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
LIMIT 1000;  -- Stops after 1000 rows
```

---

### Best Practice: Use Partition Columns

```sql
-- Leverage partition pruning
WHERE prediction_source = 'ML_PREDICTION'  -- Partition column
```

**Speed Improvement:** 2-5x faster

---

## Query Cost Estimates

| Query Type | Data Scanned | Cost | Runtime |
|------------|--------------|------|---------|
| Single PID lookup | <1 MB | <$0.01 | <1 sec |
| Filtered aggregate (60%+) | ~12 GB | $3.10 | 10-20 sec |
| Full table scan | ~15 GB | $3.75 | 20-30 sec |
| Export (80%+ confidence) | ~12 GB | $3.50 | 5-10 min |

**Athena Pricing:** $5 per TB scanned

---

## Query Optimization Tips

1. **Use WHERE clauses** to reduce data scanned
2. **Add LIMIT** for exploratory queries
3. **Use partition columns** (prediction_source)
4. **Use APPROX functions** for estimates
5. **Cache frequently-used results** (CREATE TABLE AS SELECT)
6. **Avoid SELECT *** - specify columns needed
7. **Use columnar format advantages** - Parquet is optimized for column scans

---

## Additional Resources

- **Schema Details:** `04-data-schema.md`
- **Confidence Interpretation:** `03-interpreting-confidence.md`
- **Performance Tips:** `08-troubleshooting.md`
- **Quick Start:** `11-quick-start.md`

---

**Happy Querying!** 🚀
