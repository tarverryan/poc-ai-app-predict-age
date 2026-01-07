# Age Prediction Model - Cost and Performance Analysis

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Production Status:** Deployed

---

## Cost Summary

### Per-Run Cost (Q3 2025 Production)

| Component | Unit Cost | Quantity | Total Cost |
|-----------|-----------|----------|------------|
| **Fargate Training** | $0.30 | 1 task (16 vCPU, 64GB, 15 min) | $0.30 |
| **Fargate Prediction** | $0.0155/task | 898 tasks (4 vCPU, 16GB, ~2 min avg) | $13.92 |
| **Lambda Executions** | <$0.01 | 6 functions × ~10 invocations | $0.25 |
| **Athena Queries** | $5/TB | ~0.1 TB scanned | $0.50 |
| **S3 Storage (temp)** | $0.023/GB | ~15 GB (transient) | $0.03 |
| **CloudWatch Logs** | $0.50/GB | ~0.1 GB | $0.05 |
| **TOTAL PER RUN** | | | **$15.05** |

**Annual Cost (4 quarterly runs):** ~**$60**

---

### Storage Costs (Monthly)

| Data Type | Size | Cost/Month |
|-----------|------|------------|
| **Raw Training Data** (14M PIDs, JSON) | 4.2 GB | $0.10 |
| **Raw Production Data** (378M PIDs, JSON) | 42 GB | $0.97 |
| **Final Results** (378M PIDs, Parquet) | 15 GB | $0.35 |
| **Models** (3 models, joblib) | 50 MB | <$0.01 |
| **Logs** (7-day retention) | ~1 GB | $0.50 |
| **TOTAL STORAGE** | ~62 GB | **$1.92/month** |

**Annual Storage Cost:** ~**$23**

---

### Total Cost of Ownership (TCO)

| Cost Category | Annual Cost |
|---------------|-------------|
| **Pipeline Execution** (4 runs) | $60 |
| **Storage** (S3 + Logs) | $23 |
| **Athena** (ad-hoc queries) | $20 |
| **Infrastructure** (Step Functions, ECR) | $5 |
| **TOTAL ANNUAL TCO** | **$108** |

**Cost per PID:** $0.000286 (less than $0.0003 per person)  
**Cost per Prediction:** $0.000255 (less than $0.0003 per ML prediction)

---

## Cost Optimization Strategies

### 1. Smart Filtering (Implemented)

**Impact:** 37.5% cost reduction on prediction compute

**Before Optimization:**
- Predict for ALL 378M PIDs
- Cost: ~$22 for prediction stage

**After Optimization:**
- Predict only for PIDs missing age data (236M, 62.5%)
- Cost: ~$14 for prediction stage
- **Savings: $8 per run** ($32/year)

**Implementation:**
```sql
-- Only query PIDs without age data
WHERE (birth_year IS NULL AND approximate_age IS NULL)
```

---

### 2. Inline JSON Parsing (Implemented)

**Impact:** Eliminated separate ETL step

**Before:**
- Step 1: Parse JSON to Parquet (Fargate) - $30
- Step 2: Predict from Parquet (Fargate) - $14
- Total: $44

**After:**
- Combined: Parse + Predict inline (Fargate) - $14
- **Savings: $30 per run** ($120/year)

---

### 3. Parquet Compression (Implemented)

**Impact:** 90% storage reduction

**Before (JSON):**
- Size: 150 GB
- Storage: $3.45/month
- Query cost: $7.50/query (30 GB scanned)

**After (Parquet):**
- Size: 15 GB
- Storage: $0.35/month
- Query cost: $0.75/query (3 GB scanned)
- **Savings: $3.10/month storage, $6.75/query**

---

### 4. Parallel Processing (Implemented)

**Impact:** 10x speed improvement (not cost, but faster = less risk)

**Before (sequential):**
- Runtime: ~4 hours
- Cost: Same (pay for total compute time)

**After (parallel, 500 concurrent):**
- Runtime: ~25 minutes
- Cost: Same
- **Benefit: Faster feedback, lower operational risk**

---

### Future Optimizations (Not Yet Implemented)

#### 5. Fargate Spot Instances

**Potential Impact:** 70% reduction on prediction compute

**Current:**
- Fargate On-Demand: $13.92/run

**With Spot:**
- Fargate Spot: ~$4.18/run
- **Potential Savings: $9.74/run** ($39/year)

**Trade-off:**
- 2-5% chance of task interruption
- Requires retry logic (already have)
- **Recommendation:** Implement in Q1 2026

---

#### 6. Reduce Training Frequency

**Potential Impact:** 50% reduction on training cost (minimal overall impact)

**Current:** Train every quarter (4 times/year)  
**Alternative:** Train bi-annually (2 times/year)

**Savings:** 2 × $0.30 = $0.60/year (negligible)

**Trade-off:** Potential model drift

**Recommendation:** Not worth it; continue quarterly training

---

#### 7. Model Compression

**Potential Impact:** 10-20% speed improvement on prediction

**Current:** Models total 50 MB, loaded per task

**Optimized:** Quantize models to 10 MB

**Savings:** Faster loading (~5 sec saved per task)  
**Overall impact:** ~5% runtime reduction = ~$0.70/run

**Recommendation:** Low priority

---

## Performance Metrics

### Pipeline Execution Performance

| Stage | Duration | vCPU | Memory | Tasks | Cost |
|-------|----------|------|--------|-------|------|
| **PreCleanup** | 30 sec | 0.25 | 512 MB | 1 Lambda | <$0.01 |
| **Training** | 15 min | 16 | 64 GB | 1 Fargate | $0.30 |
| **BatchGen** | <1 sec | 0.25 | 256 MB | 1 Lambda | <$0.01 |
| **CreateTable** | 5 sec | 0.25 | 512 MB | 1 Lambda | <$0.01 |
| **Prediction** | 25 min | 4 × 898 | 16 GB × 898 | 898 Fargate | $13.92 |
| **HumanQA** | 2 min | 0.5 | 1 GB | 1 Lambda | $0.05 |
| **FinalResults** | 2 min | 1.0 | 2 GB | 1 Lambda | $0.10 |
| **PostCleanup** | 1 min | 0.25 | 512 MB | 1 Lambda | <$0.01 |
| **TOTAL** | **~45 min** | | | | **$14.42** |

---

### Prediction Performance (Main Workload)

**Configuration:**
- Parallel Tasks: 898
- Max Concurrency: 500
- Per-Task Resources: 4 vCPU, 16 GB RAM
- Avg Task Duration: ~2 minutes
- PIDs per Task: ~263,000 (varies by batch)

**Throughput:**
- Per Task: ~2,192 predictions/second
- Aggregate (500 concurrent): ~1,096,000 predictions/second
- Total Predictions: 236,296,501 in 25 minutes

**Efficiency:**
- CPU Utilization: ~60-70% (good, not over/under-provisioned)
- Memory Utilization: ~40-50% (adequate headroom)
- Network I/O: Minimal (data from Athena, models from S3)

---

### Training Performance

**Configuration:**
- Task Resources: 16 vCPU, 64 GB RAM
- Training Set: 1M sample from 14M total
- Models Trained: 3 (Ridge, XGBoost, Quantile Forest)
- Duration: ~15 minutes

**Breakdown:**
- Data Loading: ~3 minutes (Athena query + transfer)
- Feature Engineering: ~2 minutes
- Ridge Training: ~1 minute
- XGBoost Training: ~6 minutes
- Quantile Training: ~2 minutes
- Model Evaluation: ~1 minute

**Efficiency:**
- CPU Utilization: ~80-90% during training (good)
- Memory Utilization: ~30-40% (adequate)
- I/O: ~100 MB/s (Athena to Fargate)

---

### Query Performance (Athena)

**Common Queries:**

| Query Type | Data Scanned | Duration | Cost |
|------------|--------------|----------|------|
| **Single PID Lookup** | <1 MB | <1 sec | <$0.01 |
| **Filtered Aggregate (60%+)** | ~12 GB | 10-20 sec | $3.10 |
| **Full Table Scan** | ~15 GB | 20-30 sec | $3.75 |
| **Age Distribution** | ~3 GB | 5-10 sec | $0.75 |
| **Export (80%+ confidence)** | ~10 GB | 2-5 min | $2.50 |

**Optimization:**
- Partitioning by `prediction_source` reduces scan by ~40%
- Parquet columnar format reduces scan by ~90%

---

## Scalability Analysis

### Current Scale (Q3 2025)

- **PIDs:** 378,024,173
- **ML Predictions:** 236,296,501
- **Batches:** 898
- **Concurrency:** 500
- **Runtime:** 45 minutes
- **Cost:** $15/run

---

### Projected Scale (Q4 2026)

Assuming 3x growth:

- **PIDs:** 1,134,072,519 (1.1B)
- **ML Predictions:** 708,889,503 (62.5%)
- **Batches:** 2,363 (300K per batch)
- **Concurrency:** 500 (same, limited by AWS quota)
- **Runtime:** ~75 minutes (linear scaling with fixed concurrency)
- **Cost:** $45/run (3x compute)

**Bottlenecks:**
- Fargate task limit (500 concurrent)
- Athena query result size (10 GB limit)

**Mitigation:**
- Request AWS quota increase (500 → 1,000 tasks)
- Increase batch size (300K → 500K per batch)
- Use S3 Select instead of Athena for very large queries

---

### Cost Scaling

| PIDs | ML Predictions | Batches | Runtime | Cost/Run | Annual (4x) |
|------|---------------|---------|---------|----------|-------------|
| 378M | 236M | 898 | 45 min | $15 | $60 |
| 750M | 469M | 1,563 | 60 min | $30 | $120 |
| 1.1B | 709M | 2,363 | 75 min | $45 | $180 |
| 1.5B | 938M | 3,125 | 90 min | $60 | $240 |

**Cost per PID remains constant (~$0.0003) due to linear scaling.**

---

## Cost Comparison

### Build vs Buy

**Build (Our Solution):**
- Per-run cost: $15
- Annual cost: $60 (4 runs)
- Customizable features
- Full data control
- No per-query fees

**Buy (Typical SaaS Age Prediction API):**
- Per-prediction cost: $0.001 - $0.005
- Cost for 236M predictions: $236K - $1.2M per run
- Limited customization
- Data privacy concerns
- Per-query fees

**ROI: Build is 15,000x - 80,000x cheaper**

---

### Cloud Provider Comparison

**AWS (Current):**
- Fargate: $0.04048/vCPU-hour, $0.004445/GB-hour
- Athena: $5/TB scanned
- S3: $0.023/GB-month
- **Total:** $15/run

**GCP (Estimated):**
- Cloud Run: ~$0.04/vCPU-hour, ~$0.004/GB-hour (similar)
- BigQuery: $5/TB scanned (same)
- Cloud Storage: $0.020/GB-month (slightly cheaper)
- **Estimated Total:** ~$14/run (7% cheaper)

**Azure (Estimated):**
- Container Instances: ~$0.0435/vCPU-hour, ~$0.0045/GB-hour (slightly more)
- Synapse Analytics: $5/TB scanned (same)
- Blob Storage: $0.0184/GB-month (cheaper)
- **Estimated Total:** ~$16/run (7% more expensive)

**Conclusion:** AWS is competitive; minimal savings by switching clouds.

---

## Performance Benchmarks

### Industry Comparison

**Our Model:**
- MAE: 2.23 years
- Throughput: 1M predictions/second (aggregate)
- Cost: $0.0003/prediction
- Latency: Batch (25 min for 236M)

**Typical Age Prediction Services:**
- MAE: 3-5 years (worse)
- Throughput: 10-100 predictions/second (100-10,000x slower)
- Cost: $0.001-$0.005/prediction (3-17x more expensive)
- Latency: Real-time (<1 sec per prediction)

**Trade-off:** We prioritize batch throughput and cost over real-time latency.

---

## Cost Allocation

### By Stage (% of Total)

| Stage | Cost | % of Total |
|-------|------|------------|
| **Prediction** (Fargate) | $13.92 | 92.5% |
| **Training** (Fargate) | $0.30 | 2.0% |
| **Athena Queries** | $0.50 | 3.3% |
| **Lambda** | $0.25 | 1.7% |
| **Other** (S3, Logs) | $0.08 | 0.5% |
| **TOTAL** | $15.05 | 100% |

**Key Insight:** 92.5% of cost is prediction stage → Focus optimization there.

---

### By Resource Type

| Resource | Cost/Run | Annual (4x) |
|----------|----------|-------------|
| **Compute** (Fargate) | $14.22 | $56.88 |
| **Data** (Athena, S3) | $0.53 | $2.12 |
| **Serverless** (Lambda, Step Functions) | $0.30 | $1.20 |
| **TOTAL** | $15.05 | $60.20 |

---

## Monitoring and Alerts

### Cost Monitoring

**CloudWatch Metrics:**
- Fargate task duration (track for cost spikes)
- Athena data scanned (alert if >20 GB per query)
- Lambda invocations (track for unexpected runs)

**Budgets:**
- Set AWS Budget: $25/month (alert at 80% threshold)
- Monthly report on actual vs expected costs

---

### Performance Monitoring

**Key Metrics:**
- Pipeline execution time (target: <60 min, alert if >90 min)
- Fargate task success rate (target: >98%, alert if <95%)
- Athena query duration (alert if >60 sec for simple queries)
- Model accuracy (MAE, alert if >3.0 years)

**Dashboards:**
- CloudWatch Dashboard with:
  - Pipeline execution timeline
  - Fargate resource utilization
  - Cost per run (trended)
  - Prediction count per run

---

## Recommendations

### Short-Term (Q1 2026)

1. **Implement Fargate Spot** - Save $39/year
2. **Increase concurrency to 1,000** - Reduce runtime to ~15 min
3. **Set up cost alerts** - Monitor for unexpected spikes

### Medium-Term (Q2 2026)

1. **Optimize XGBoost hyperparameters** - Improve accuracy (minimal cost impact)
2. **Add S3 Intelligent-Tiering** - Save $5/year on storage
3. **Implement caching for frequent queries** - Save $10-20/year on Athena

### Long-Term (2026+)

1. **Real-time inference API** - Add Lambda endpoint (pay-per-use)
2. **Multi-region deployment** - Disaster recovery (2x cost)
3. **Model ensemble** - Better accuracy (10-20% more cost)

---

## Summary

**Current Performance:**
- ✅ 378M predictions in 45 minutes
- ✅ $15 per run ($60/year)
- ✅ 2.23 year MAE (excellent)
- ✅ 83% high quality (≥60% confidence)

**Cost Efficiency:**
- ✅ $0.0003 per prediction (15,000x cheaper than SaaS)
- ✅ 50% cost reduction vs initial design (inline parsing)
- ✅ 37% savings from smart filtering

**Scalability:**
- ✅ Linear cost scaling to 1B+ PIDs
- ✅ Bottleneck: AWS task quota (easily increased)
- ✅ 10x speed via parallelization

**Verdict: Highly cost-effective, performant, and scalable solution.**

---

**For Architecture Details:** See `09-pipeline-architecture.md`  
**For Model Performance:** See `12-model-performance.md`
