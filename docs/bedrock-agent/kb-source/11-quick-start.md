# Age Prediction Model - 5-Minute Quick Start

**Document Version:** 1.0  
**Last Updated:** October 23, 2025

---

## Welcome!

This guide gets you querying age predictions in **5 minutes or less**.

---

## Step 1: Access Athena (30 seconds)

1. Go to AWS Console → Athena
2. Region: **us-east-1**
3. Database: Select **`ai_agent_kb_predict_age`**

---

## Step 2: Your First Query (1 minute)

Copy and run this:

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

**What This Shows:**
- 10 high-quality age predictions
- Confidence scores (60%+ = good)
- Whether it's real data or ML prediction

---

## Step 3: Understand the Results (2 minutes)

### Column Meanings

| Column | What It Means | Example |
|--------|---------------|---------|
| `pid` | Person ID | 123456789 |
| `predicted_age` | Age in years | 35 |
| `confidence_pct` | Quality (0-100%, higher = better) | 75.2% |
| `prediction_source` | Where it came from | 'ML_PREDICTION' or 'EXISTING_APPROX_AGE' |

### Confidence Guide

- **100%** = Real data (best!)
- **80-100%** = Excellent ML (±2-3 years)
- **60-80%** = Good ML (±3-6 years)
- **40-60%** = Fair ML (±6-9 years)
- **<40%** = Use with caution

---

## Step 4: Try Common Use Cases (1 minute each)

### Use Case 1: Age Range Segmentation
```sql
SELECT 
    CASE 
        WHEN predicted_age < 25 THEN '18-24'
        WHEN predicted_age < 35 THEN '25-34'
        WHEN predicted_age < 45 THEN '35-44'
        WHEN predicted_age < 55 THEN '45-54'
        ELSE '55+'
    END as age_group,
    COUNT(*) as count
FROM predict_age_final_results_with_confidence
WHERE confidence_pct >= 60
GROUP BY 1
ORDER BY 1;
```

### Use Case 2: Find Specific Person
```sql
SELECT *
FROM predict_age_final_results_with_confidence
WHERE pid = 123456789;
```

### Use Case 3: Quality Distribution
```sql
SELECT 
    CASE 
        WHEN confidence_pct = 100 THEN 'Perfect'
        WHEN confidence_pct >= 80 THEN 'Excellent'
        WHEN confidence_pct >= 60 THEN 'Good'
        ELSE 'Fair/Poor'
    END as quality,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / 378024173, 1) as pct
FROM predict_age_final_results_with_confidence
GROUP BY 1
ORDER BY MIN(confidence_pct) DESC;
```

---

## Key Facts to Remember

- **Total Records:** 378 million (100% coverage)
- **High Quality (≥60%):** 314 million (83%)
- **Real Data:** 142 million (37%)
- **Table Name:** `predict_age_final_results_with_confidence`
- **Database:** `ai_agent_kb_predict_age`

---

## Next Steps

**Learn More:**
- Confidence scores: `03-interpreting-confidence.md`
- More queries: `06-example-queries.md`
- Full schema: `04-data-schema.md`

**Get Help:**
- FAQ: `05-faq.md`
- Troubleshooting: `08-troubleshooting.md`

---

**You're Ready!** Start querying age predictions now. 🚀
