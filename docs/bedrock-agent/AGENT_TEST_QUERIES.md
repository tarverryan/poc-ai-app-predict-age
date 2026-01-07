# Bedrock Agent Test Queries - Age Prediction KB

**Purpose:** Comprehensive test suite for validating Bedrock Agent responses using the Age Prediction Knowledge Base.

**Knowledge Base ID:** `WKVANDULTR`  
**Last Updated:** October 23, 2025

---

## 🎯 Test Categories (12 Categories, 100+ Queries)

---

## 1️⃣ Model Performance & Accuracy (15 queries)

### Basic Metrics
- [ ] "What's the model accuracy?"
- [ ] "What's the MAE for age predictions?"
- [ ] "What's the R² score?"
- [ ] "How accurate are the predictions?"
- [ ] "What percentage of predictions are within 5 years?"

### Performance by Segment
- [ ] "How accurate is the model for people aged 30-40?"
- [ ] "What's the performance for young employees under 25?"
- [ ] "Does accuracy vary by age group?"

### Model Comparison
- [ ] "Why was XGBoost chosen?"
- [ ] "What models were trained?"
- [ ] "How does Ridge compare to XGBoost?"
- [ ] "Which model is in production?"

### Expected Answers
- MAE: 2.23 years
- R²: 0.739
- 75% within ±5 years, 95% within ±10 years
- XGBoost chosen for 28% better MAE vs Ridge
- Best performance for ages 25-45

---

## 2️⃣ Confidence Score Queries (18 queries)

### Understanding Scores
- [ ] "What do confidence scores mean?"
- [ ] "What's the difference between confidence_score_original and confidence_pct?"
- [ ] "Why are some confidence scores negative?"
- [ ] "How do I interpret a 75% confidence score?"
- [ ] "What does 100% confidence mean?"
- [ ] "What's a good confidence score?"

### Score Distribution
- [ ] "What's the average confidence score?"
- [ ] "What percentage of predictions are high quality?"
- [ ] "How many PIDs have confidence above 80%?"
- [ ] "What's the confidence distribution?"

### Thresholds
- [ ] "What confidence threshold should I use for email marketing?"
- [ ] "What confidence level for legal compliance?"
- [ ] "What threshold for audience segmentation?"
- [ ] "When should I use 60% vs 80% confidence?"
- [ ] "Can I use 40% confidence predictions?"

### Expected Answers
- Dual system: original (interval width) + percentage (0-100%)
- Negative scores = extremely confident (quantile crossing)
- 100% = real data OR excellent ML
- 83.2% high quality (≥60%)
- Email: 80%+, Legal: 100% real only, Segmentation: 60%+

---

## 3️⃣ SQL Query Generation (20 queries)

### Basic Queries
- [ ] "Show me SQL to query the age predictions table"
- [ ] "How do I get predictions for a specific PID?"
- [ ] "Give me SQL to query ages 30-40"
- [ ] "How do I filter by confidence score?"
- [ ] "Show me the top 1000 high-confidence predictions"

### Advanced Queries
- [ ] "How do I segment by age ranges?"
- [ ] "SQL to find Millennials vs Gen X?"
- [ ] "Query to get age distribution by decade?"
- [ ] "How do I join age predictions with my employee table?"
- [ ] "SQL for random sampling?"
- [ ] "How do I export high-quality predictions?"

### Analysis Queries
- [ ] "Show me SQL for confidence distribution analysis"
- [ ] "How do I calculate average age by industry?"
- [ ] "Query to find outliers very young or old?"
- [ ] "SQL to compare real data vs ML predictions?"

### Performance Queries
- [ ] "How do I optimize my Athena queries?"
- [ ] "What's the most efficient way to query this table?"
- [ ] "How do I reduce query costs?"

### Expected Answers
- Table: `predict_age_final_results_with_confidence`
- Database: `ai_agent_kb_predict_age`
- Should provide actual SQL code (not pseudo-code)
- Include WHERE, LIMIT, and optimization tips

---

## 4️⃣ Data Schema & Structure (12 queries)

### Table Information
- [ ] "What tables are available?"
- [ ] "What's the schema for the predictions table?"
- [ ] "What columns are in the final results table?"
- [ ] "Where is the data stored in S3?"

### Data Sources
- [ ] "How many PIDs have predictions?"
- [ ] "What's the difference between real data and ML predictions?"
- [ ] "How many PIDs have existing age data?"
- [ ] "What percentage is ML vs real data?"

### Data Quality
- [ ] "Are there any null values?"
- [ ] "How complete is the data?"
- [ ] "Are there any missing predictions?"

### Expected Answers
- 378M total PIDs, 100% coverage
- 141.7M real (37.5%), 236.3M ML (62.5%)
- Columns: pid, predicted_age, confidence_score_original, confidence_pct, prediction_source
- No nulls in final table

---

## 5️⃣ Features & Model Inputs (15 queries)

### Feature Information
- [ ] "What features does the model use?"
- [ ] "What's the most important feature for predicting age?"
- [ ] "How many features are there?"
- [ ] "What's tenure_months?"
- [ ] "Explain linkedin_connection_count"
- [ ] "What does job_level_encoded mean?"

### Feature Importance
- [ ] "Which features are most predictive?"
- [ ] "What's the feature importance ranking?"
- [ ] "What contributes most to age predictions?"
- [ ] "What's the top 5 features?"

### Feature Engineering
- [ ] "How is total_career_years calculated?"
- [ ] "What's the difference between tenure_months and company_tenure_years?"
- [ ] "How are categorical features encoded?"

### Expected Answers
- 22 features total
- Top feature: total_career_years (23.4%)
- Top 5: total_career_years, tenure_months, job_level_encoded, education_level_encoded, work_experience_count
- Should explain feature meaning and encoding

---

## 6️⃣ Cost & Performance (12 queries)

### Pipeline Costs
- [ ] "How much does it cost to run the pipeline?"
- [ ] "What's the cost per prediction?"
- [ ] "How much does it cost per year?"
- [ ] "What are the main cost drivers?"
- [ ] "How can I reduce costs?"

### Query Costs
- [ ] "How much do Athena queries cost?"
- [ ] "What's the cost to scan the full table?"
- [ ] "How can I minimize query costs?"

### Performance Metrics
- [ ] "How long does the pipeline take?"
- [ ] "How many predictions per second?"
- [ ] "How does it scale to 1 billion PIDs?"

### Expected Answers
- $15 per run, $60 per year (quarterly)
- 45 minutes total runtime
- 1M predictions/second aggregate
- Cost driver: Fargate prediction (92.5% of cost)
- Optimization: smart filtering, inline parsing, Fargate Spot

---

## 7️⃣ Pipeline Architecture & Technical (15 queries)

### Architecture
- [ ] "How does the pipeline work?"
- [ ] "What AWS services are used?"
- [ ] "Explain the Step Functions workflow"
- [ ] "How many Fargate tasks run?"
- [ ] "What's parallel processing?"

### Technical Details
- [ ] "What's the training container?"
- [ ] "Where are models stored?"
- [ ] "How is batching done?"
- [ ] "What's the IAM setup?"

### Infrastructure
- [ ] "What database is used?"
- [ ] "What's the S3 path structure?"
- [ ] "How are logs stored?"
- [ ] "What region is this in?"

### Expected Answers
- 8-stage Step Functions pipeline
- 898 Fargate tasks, max 500 concurrent
- Services: Fargate, Lambda, Athena, S3, Step Functions
- Database: ai_agent_kb_predict_age
- Region: us-east-1

---

## 8️⃣ Business Use Cases & Guidelines (18 queries)

### Use Case Recommendations
- [ ] "What can I use age predictions for?"
- [ ] "Can I use this for personalized email?"
- [ ] "What confidence level for marketing campaigns?"
- [ ] "Can I use predictions for legal compliance?"
- [ ] "What's the best use case for 60% confidence?"
- [ ] "Should I use this for CRM enrichment?"

### Business Value
- [ ] "What's the ROI of this model?"
- [ ] "How much coverage improvement vs before?"
- [ ] "What's the business impact?"
- [ ] "How many new predictions do we get?"

### Best Practices
- [ ] "What are the best practices for using predictions?"
- [ ] "Should I use exact ages or age ranges?"
- [ ] "How do I combine age with other features?"
- [ ] "What should I avoid?"
- [ ] "Can I use this for age-restricted content?"

### Expected Answers
- Use cases: marketing, segmentation, profile enrichment, ML features
- 62.5% coverage improvement (236M new predictions)
- Use ranges, not exact ages
- NEVER use ML for legal/compliance (100% real data only)

---

## 9️⃣ Troubleshooting & Errors (15 queries)

### Common Errors
- [ ] "Why am I getting a type mismatch error?"
- [ ] "My query timed out, what do I do?"
- [ ] "I'm getting table not found error"
- [ ] "Why is my query so slow?"
- [ ] "How do I fix Access Denied errors?"

### Data Issues
- [ ] "Why do some PIDs have low confidence?"
- [ ] "Why are predictions missing for some PIDs?"
- [ ] "What does a negative confidence score mean?"
- [ ] "Why is the predicted age 18 for someone senior?"

### Performance Issues
- [ ] "How do I speed up my queries?"
- [ ] "My query cost $20, why?"
- [ ] "Why is my join so slow?"

### Expected Answers
- Type mismatch: pid is BIGINT not VARCHAR
- Timeout: add WHERE + LIMIT
- Negative scores: extremely confident (not errors)
- Low confidence: sparse profile data
- High cost: scanning too much data, add filters

---

## 🔟 Getting Started & Quick Reference (10 queries)

### Quick Start
- [ ] "How do I get started?"
- [ ] "Show me a simple query example"
- [ ] "What's the main table to query?"
- [ ] "Give me the 5-minute quick start"

### Common Tasks
- [ ] "How do I find high-quality predictions?"
- [ ] "How do I segment by generation?"
- [ ] "How do I export data?"
- [ ] "How do I validate predictions?"

### Expected Answers
- Start with doc 11-quick-start.md
- Main table: predict_age_final_results_with_confidence
- Provide working SQL example
- Link to relevant docs

---

## 1️⃣1️⃣ Persona-Specific Queries (20 queries)

### Data Scientists
- [ ] "How was the model trained?"
- [ ] "What's the train/test split?"
- [ ] "What hyperparameters were used?"
- [ ] "How do I retrain the model?"
- [ ] "What's the cross-validation performance?"

### Analysts
- [ ] "How do I analyze age distribution?"
- [ ] "What's the age breakdown by industry?"
- [ ] "How do I create age cohorts?"
- [ ] "What's the median age?"

### Engineers
- [ ] "How do I integrate this with my ETL?"
- [ ] "How do I schedule quarterly runs?"
- [ ] "What's the API endpoint?"
- [ ] "What's the Docker image?"

### Marketing/Business
- [ ] "How do I target 25-34 year olds?"
- [ ] "What confidence for personalized campaigns?"
- [ ] "Can I use this for lookalike audiences?"

### Compliance/Legal
- [ ] "Can I use this for age-restricted content?"
- [ ] "What's the accuracy for legal purposes?"
- [ ] "How do I identify real data vs predictions?"

### Expected Answers
- Training: 1M from 14M, 80/20 split
- Hyperparameters: XGBoost defaults (n_estimators=200)
- Median age: 34 years
- No API yet (planned Q1 2026)
- Legal: NEVER use ML, only 100% real data

---

## 1️⃣2️⃣ Advanced/Complex Queries (10 queries)

### Multi-Step Analysis
- [ ] "Show me age distribution, filter to high confidence, then segment by decade"
- [ ] "What's the accuracy for predictions in the tech industry for people 30-40?"
- [ ] "Compare confidence scores between real data and ML predictions by age group"

### Integration Questions
- [ ] "How do I join this with Salesforce data?"
- [ ] "Can I use this in Redshift?"
- [ ] "How does this integrate with the job-change model?"

### Optimization Questions
- [ ] "What's the optimal confidence threshold for my use case?"
- [ ] "Should I use Fargate Spot instances?"
- [ ] "How do I cache frequent queries?"

### Expected Answers
- Provide multi-step SQL queries
- Explain integration patterns
- Recommend optimization based on use case

---

## ✅ Success Criteria

**Agent passes if it can:**

1. **Answer ≥90% of queries correctly** (90/100+)
2. **Provide SQL code** when requested (not pseudo-code)
3. **Reference specific documents** (e.g., "See doc 03 for details")
4. **Cite actual metrics** (2.23 MAE, 378M PIDs, 83% high quality)
5. **Give actionable guidance** (thresholds, best practices, next steps)
6. **Handle follow-ups** (conversational context)
7. **Admit uncertainty** when KB doesn't have info
8. **Cross-reference** related topics across documents

---

## 🧪 Testing Protocol

### Phase 1: Smoke Test (10 queries)
Select 10 high-priority queries from different categories, test basic functionality.

### Phase 2: Category Testing (12 categories)
Test 5-10 queries per category systematically.

### Phase 3: Edge Cases
Test ambiguous queries, multi-step questions, error scenarios.

### Phase 4: Conversational Flow
Test follow-up questions, context retention, clarifications.

### Phase 5: Production Readiness
Test with real user questions, validate SQL output, verify metrics.

---

## 📊 Scoring Rubric

| Score | Criteria |
|-------|----------|
| **5** | Perfect answer with code, metrics, and doc references |
| **4** | Correct answer, minor omissions or formatting issues |
| **3** | Partially correct, missing key details or context |
| **2** | Incorrect but related info, shows KB access |
| **1** | Wrong answer or unable to retrieve info |
| **0** | No response or completely irrelevant |

**Target Average:** ≥4.0 across all queries

---

## 🔄 Iteration Log

### Iteration 1: Initial Agent Creation
- Date: [TBD]
- Agent ID: [TBD]
- KB ID: WKVANDULTR
- Model: [TBD]
- Results: [TBD]

### Iteration 2+: Refinements
- [Document improvements based on testing]

---

**Total Queries:** 168 distinct test queries  
**Categories:** 12  
**Expected Completion:** Agent can handle all common use cases

