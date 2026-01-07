# Age Prediction Model - Troubleshooting Guide

**Document Version:** 1.0  
**Last Updated:** October 23, 2025

---

## Quick Troubleshooting

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| Query timeout | Scanning too much data | Add WHERE clause + LIMIT |
| Type mismatch error | pid as VARCHAR vs BIGINT | Cast types: `WHERE pid = 123456789` (not '123456789') |
| Low confidence scores | Sparse profile data | Use lower confidence threshold or enrich profiles |
| Negative confidence scores | Quantile regression quirk | Treat as 100% confidence (excellent) |
| Missing predictions | PID not in dataset | Check PID exists in source data |
| Unexpected age (very young/old) | Edge case or sparse data | Check confidence score and profile completeness |

---

## Query Issues

### Issue 1: Query Timeout / Resource Exhaustion

**Error:**
```
Query exhausted resources at this scale factor
HIVE_CURSOR_ERROR: Timeout waiting for results
```

**Cause:** Query scanning too much data (full table = 15 GB)

**Solutions:**

**Solution A: Add WHERE Clause**
```sql
-- Before (scans all 378M rows)
SELECT * FROM predict_age_final_results_with_confidence;

-- After (scans subset)
SELECT * FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
LIMIT 10000;
```

**Solution B: Use Partition Pruning**
```sql
-- Leverage partition column
WHERE prediction_source = 'ML_PREDICTION';
```

**Solution C: Use APPROX Functions**
```sql
-- Use approximate aggregates (10x faster)
SELECT APPROX_DISTINCT(pid) FROM table;
```

---

### Issue 2: Type Mismatch Errors

**Error:**
```
TYPE_MISMATCH: Cannot apply operator: varchar = bigint
Column 'pid' is type bigint but expression is type varchar
```

**Cause:** PID column is BIGINT, not VARCHAR

**Solution:**
```sql
-- Wrong
WHERE pid = '123456789'  -- String literal

-- Correct
WHERE pid = 123456789  -- Integer literal

-- Or cast explicitly
WHERE CAST(pid AS VARCHAR) = '123456789'
```

---

### Issue 3: Column Not Found

**Error:**
```
COLUMN_NOT_FOUND: Column 'confidence_score' cannot be resolved
```

**Cause:** Column name typo or doesn't exist

**Solution:**
Check correct column names:
- `confidence_score_original` (not `confidence_score`)
- `confidence_pct` (not `confidence_percent`)
- `predicted_age` (not `age` or `prediction`)

**List all columns:**
```sql
DESCRIBE predict_age_final_results_with_confidence;
```

---

### Issue 4: Table Not Found

**Error:**
```
TABLE_NOT_FOUND: Table 'predict_age_final_results' does not exist
```

**Cause:** Incorrect table name or database not selected

**Solution:**
```sql
-- Use fully qualified name
SELECT * FROM ai_agent_kb_predict_age.predict_age_final_results_with_confidence;

-- Or set database first
USE ai_agent_kb_predict_age;
SELECT * FROM predict_age_final_results_with_confidence;
```

**Verify table exists:**
```sql
SHOW TABLES IN ai_agent_kb_predict_age LIKE 'predict%';
```

---

### Issue 5: Permission Denied

**Error:**
```
Access Denied: User does not have permission to read table
```

**Cause:** IAM permissions not granted

**Solution:**
Contact your AWS administrator to grant:
- `athena:GetQueryResults`
- `s3:GetObject` on `s3://${S3_BUCKET}/predict-age/`
- `glue:GetTable` on `ai_agent_kb_predict_age` database

---

## Data Quality Issues

### Issue 6: Low Confidence Scores

**Symptom:** Many predictions with <60% confidence

**Cause:** Sparse profile data (missing features)

**Diagnosis:**
```sql
-- Check confidence distribution
SELECT 
    CASE 
        WHEN confidence_pct >= 80 THEN 'Excellent'
        WHEN confidence_pct >= 60 THEN 'Good'
        WHEN confidence_pct >= 40 THEN 'Fair'
        ELSE 'Poor'
    END as tier,
    COUNT(*) as count
FROM predict_age_final_results_with_confidence
WHERE prediction_source = 'ML_PREDICTION'
GROUP BY 1;
```

**Solutions:**

**A. Use Lower Confidence Threshold**
- Accept 40%+ for low-risk applications
- Understand margin of error increases

**B. Profile Enrichment**
- Add missing LinkedIn data
- Fill in education, skills, work history

**C. Focus on High-Confidence Subset**
- Filter to confidence_pct >= 60 (still 83% coverage)

---

### Issue 7: Negative Confidence Scores

**Symptom:** `confidence_score_original` is negative (e.g., -0.45)

**Is This a Problem?** **No! This indicates extremely high confidence.**

**Explanation:**
Quantile regression can produce "crossing quantiles" when very confident:
- pred_5th = 35.2 years
- pred_95th = 34.8 years
- confidence = 34.8 - 35.2 = **-0.4**

**Solution:** Treat as excellent predictions (100% confidence)

The `confidence_pct` column already handles this (capped at 100%).

---

### Issue 8: Unexpected Ages (Very Young or Very Old)

**Symptom:** Predicted age <20 or >70

**Diagnosis:**
```sql
-- Find outliers
SELECT pid, predicted_age, confidence_pct, prediction_source
FROM predict_age_final_results_with_confidence
WHERE (predicted_age < 20 OR predicted_age > 70)
  AND prediction_source = 'ML_PREDICTION'
ORDER BY predicted_age
LIMIT 100;
```

**Causes:**
1. **Edge Cases** - Model trained on 25-55 age range (less data at extremes)
2. **Sparse Profiles** - Low feature coverage → Less accurate
3. **Rare Career Patterns** - Unusual career trajectories

**Solutions:**
- Check `confidence_pct` (low confidence expected for edge cases)
- Validate with additional data sources
- Consider excluding extremes for sensitive applications

---

### Issue 9: Missing Predictions

**Symptom:** PID exists in source data but not in predictions table

**Diagnosis:**
```sql
-- Check if PID exists in source
SELECT pid, birth_year, approximate_age
FROM ai_agent_kb_predict_age.predict_age_full_evaluation_raw_378m
WHERE pid = 123456789;

-- Check if PID exists in predictions
SELECT * FROM predict_age_final_results_with_confidence
WHERE pid = 123456789;
```

**Causes:**
1. **PID Added After Model Run** - Data refreshed after Q3 2025 run
2. **Data Filter** - PID filtered out during processing
3. **Processing Error** - Rare batch processing failure

**Solutions:**
- Verify PID exists in Q3 2025 source data
- Trigger model rerun (quarterly) to include new PIDs
- Contact #predict-age if urgent

---

### Issue 10: Confidence Score Doesn't Match Intuition

**Symptom:** High confidence_pct but age seems wrong (or vice versa)

**Understanding:**
- Confidence reflects **data completeness**, not **individual certainty**
- A complete profile (20+ features) → High confidence, even if prediction is wrong

**Diagnosis:**
Check feature completeness in source data:
```sql
-- Count features available for PID
SELECT 
    pid,
    CASE WHEN tenure_months IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN linkedin_connection_count IS NOT NULL THEN 1 ELSE 0 END +
    CASE WHEN job_level_encoded IS NOT NULL THEN 1 ELSE 0 END +
    ... -- (sum all 22 features)
    as feature_count
FROM source_table
WHERE pid = 123456789;
```

**Insight:** High feature count → High confidence, regardless of correctness

---

## Performance Issues

### Issue 11: Slow Joins

**Symptom:** Query joining age predictions with other tables takes >60 seconds

**Diagnosis:**
```sql
-- Check join key distribution
SELECT 
    COUNT(DISTINCT pid) as unique_pids,
    COUNT(*) as total_rows
FROM your_table;
```

**Solutions:**

**A. Ensure PID is Indexed**
Age predictions table is already optimized (Parquet partitioned)

**B. Filter Before Join**
```sql
-- Good: Filter first, join second
SELECT ...
FROM (
    SELECT pid, predicted_age FROM predictions WHERE confidence_pct >= 60
) a
JOIN your_table b ON a.pid = b.pid;

-- Bad: Join first, filter second
SELECT ...
FROM predictions a
JOIN your_table b ON a.pid = b.pid
WHERE a.confidence_pct >= 60;
```

**C. Broadcast Join Hint (if joining with small table)**
```sql
-- Force broadcast join for small table
SELECT /*+ BROADCAST(small_table) */ ...
FROM large_table
JOIN small_table ON ...;
```

---

### Issue 12: High Query Costs

**Symptom:** Athena costs higher than expected ($10+ per query)

**Diagnosis:**
Check data scanned:
- Athena console shows "Data scanned: X GB"
- Cost = Data scanned (GB) / 1000 × $5

**Solutions:**

**A. Always Add WHERE Clause**
```sql
WHERE confidence_pct >= 60  -- Reduces scan by ~17%
```

**B. Select Only Needed Columns**
```sql
-- Good: Select specific columns
SELECT pid, predicted_age FROM table;

-- Bad: Select all columns (scans more data)
SELECT * FROM table;
```

**C. Use LIMIT for Exploratory Queries**
```sql
SELECT * FROM table LIMIT 1000;
```

**D. Cache Frequently-Used Results**
```sql
CREATE TABLE my_filtered_predictions AS
SELECT * FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60;

-- Now query cached table (faster, cheaper)
SELECT * FROM my_filtered_predictions;
```

---

## Integration Issues

### Issue 13: CRM Import Fails

**Symptom:** Salesforce/HubSpot import rejects age data

**Common Causes:**
1. **Field Type Mismatch** - Age as VARCHAR instead of INTEGER
2. **Invalid Values** - NULL or negative ages
3. **Bulk Limit Exceeded** - Too many records in single import

**Solutions:**

**A. Validate Data Before Export**
```sql
SELECT 
    pid,
    predicted_age,
    confidence_pct
FROM predict_age_final_results_with_confidence
WHERE predicted_age IS NOT NULL
  AND predicted_age BETWEEN 18 AND 75
  AND confidence_pct >= 70
LIMIT 50000;  -- Match CRM bulk limit
```

**B. Export in CRM-Compatible Format**
```sql
UNLOAD (
    SELECT 
        CAST(pid AS VARCHAR) as contact_id,
        CAST(predicted_age AS INTEGER) as age,
        CAST(ROUND(confidence_pct, 0) AS VARCHAR) || '%' as confidence
    FROM predict_age_final_results_with_confidence
    WHERE confidence_pct >= 70
)
TO 's3://bucket/crm-import/'
WITH (format = 'CSV', field_delimiter = ',', header = true);
```

---

### Issue 14: API Rate Limiting

**Symptom:** Loading predictions into downstream system fails with 429 errors

**Solution:** Batch API calls
```python
# Python example: Batch updates
import boto3
import time

athena = boto3.client('athena')

# Fetch in batches
for offset in range(0, 1000000, 10000):
    query = f"""
        SELECT pid, predicted_age, confidence_pct
        FROM predict_age_final_results_with_confidence
        WHERE confidence_pct >= 60
        LIMIT 10000 OFFSET {offset}
    """
    
    # Execute query
    result = athena.start_query_execution(...)
    
    # Process batch
    # ...
    
    # Rate limit
    time.sleep(1)  # 1 second between batches
```

---

## Model Issues

### Issue 15: Model Performance Degraded

**Symptom:** Predictions seem less accurate than before

**Diagnosis:**

**A. Check Model Version**
```sql
SELECT qa_timestamp, COUNT(*)
FROM predict_age_final_results_with_confidence
GROUP BY 1;
```

**B. Compare Confidence Distribution Over Time**
```sql
-- Compare current vs previous run
SELECT 
    'Current (2025-Q3)' as run,
    AVG(confidence_pct) as avg_confidence
FROM predict_age_final_results_with_confidence
UNION ALL
SELECT 
    'Previous (2025-Q2)' as run,
    AVG(confidence_pct) as avg_confidence
FROM predict_age_final_results_2025q2;
```

**Causes:**
1. **Data Drift** - Career patterns changed (retrain quarterly)
2. **Feature Coverage Declined** - Source data quality decreased
3. **New Population** - More sparse profiles added

**Solutions:**
- Trigger model retraining
- Investigate source data quality
- Contact #predict-age for analysis

---

### Issue 16: Feature Missing in Source Data

**Symptom:** Expected feature (e.g., linkedin_connection_count) is NULL for many PIDs

**Diagnosis:**
```sql
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN linkedin_connection_count IS NULL THEN 1 ELSE 0 END) as null_count,
    ROUND(SUM(CASE WHEN linkedin_connection_count IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as null_pct
FROM ai_agent_kb_predict_age.predict_age_full_evaluation_raw_378m;
```

**Causes:**
1. **Data Source Changed** - LinkedIn API access revoked
2. **ETL Pipeline Issue** - Feature extraction failed
3. **Expected Sparsity** - Feature naturally sparse (e.g., certifications)

**Solutions:**
- Check ETL logs
- Validate upstream data source
- Model handles missing values (uses imputation)

---

## Emergency Procedures

### Procedure 1: Rollback to Previous Model

**When:** Current model producing poor predictions

**Steps:**
1. Verify previous model exists:
   ```sql
   SHOW TABLES IN ai_agent_kb_predict_age LIKE '%2025q2%';
   ```

2. Create view pointing to previous model:
   ```sql
   CREATE OR REPLACE VIEW predict_age_final_results_with_confidence AS
   SELECT * FROM predict_age_final_results_2025q2;
   ```

3. Update downstream systems to use view

4. Investigate current model issue

---

### Procedure 2: Hotfix Individual Predictions

**When:** Specific PIDs have known incorrect predictions

**Steps:**
1. Create override table:
   ```sql
   CREATE TABLE age_prediction_overrides (
       pid BIGINT,
       corrected_age INTEGER,
       reason VARCHAR,
       override_date DATE
   );
   ```

2. Insert corrections:
   ```sql
   INSERT INTO age_prediction_overrides VALUES
   (123456789, 42, 'Customer reported age', CURRENT_DATE);
   ```

3. Create view with overrides:
   ```sql
   CREATE OR REPLACE VIEW predict_age_with_overrides AS
   SELECT 
       COALESCE(o.pid, p.pid) as pid,
       COALESCE(o.corrected_age, p.predicted_age) as predicted_age,
       CASE WHEN o.pid IS NOT NULL THEN 100.0 ELSE p.confidence_pct END as confidence_pct,
       CASE WHEN o.pid IS NOT NULL THEN 'MANUAL_OVERRIDE' ELSE p.prediction_source END as prediction_source
   FROM predict_age_final_results_with_confidence p
   LEFT JOIN age_prediction_overrides o ON p.pid = o.pid;
   ```

---

## Getting Help

### Self-Service Resources

1. **Documentation:** `/docs/bedrock-agent/kb-source/`
2. **FAQ:** `05-faq.md`
3. **Example Queries:** `06-example-queries.md`
4. **Quick Start:** `11-quick-start.md`

---

### Escalation Path

**Level 1: Slack** (#predict-age channel)
- Query issues
- Data quality questions
- Usage guidance

**Level 2: Data Science Team**
- Model performance issues
- Feature engineering questions
- Retraining requests

**Level 3: On-Call**
- Production outages
- Data corruption
- Critical business impact

---

## Common Error Codes

| Error Code | Meaning | Fix |
|------------|---------|-----|
| `HIVE_CURSOR_ERROR` | Query timeout | Add WHERE + LIMIT |
| `TYPE_MISMATCH` | Column type wrong | Cast types correctly |
| `COLUMN_NOT_FOUND` | Column doesn't exist | Check spelling, use DESCRIBE |
| `TABLE_NOT_FOUND` | Table doesn't exist | Use full name: `db.table` |
| `ACCESS_DENIED` | No permissions | Contact AWS admin |
| `SYNTAX_ERROR` | Invalid SQL | Check syntax, semicolons |

---

## Preventive Measures

### Best Practices

1. **Always test queries on small LIMIT first**
   ```sql
   SELECT * FROM table WHERE ... LIMIT 100;  -- Test first
   ```

2. **Use Views for common filters**
   ```sql
   CREATE VIEW high_quality_predictions AS
   SELECT * FROM predictions WHERE confidence_pct >= 60;
   ```

3. **Monitor query costs**
   - Check Athena console for data scanned
   - Set up CloudWatch alerts for high costs

4. **Document custom queries**
   - Save frequently-used queries
   - Share with team

5. **Validate assumptions**
   - Spot-check predictions
   - Compare with known ages
   - Monitor confidence distribution

---

**Still Stuck?** Contact #predict-age on Slack with:
- Error message (full text)
- Query executed (sanitized)
- Expected vs actual behavior
- Any relevant PIDs (for debugging)
