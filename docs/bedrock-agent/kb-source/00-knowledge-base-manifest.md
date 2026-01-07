# Knowledge Base Manifest

**Knowledge Base Name:** Age Prediction Model - Agent Context  
**Version:** 1.0  
**Last Updated:** October 23, 2025  
**S3 Location:** s3://${S3_BUCKET}/predict-age/agent-context-upload/  
**Purpose:** Comprehensive context for Bedrock Agent natural language query interface

---

## Document Inventory

| # | Document | Purpose | Size | Pages |
|---|----------|---------|------|-------|
| 00 | `00-knowledge-base-manifest.md` | This file - inventory and index | ~12KB | 5 |
| 01 | `01-model-overview.md` | Complete model overview, architecture, training data | ~60KB | 38 |
| 02 | `02-features.md` | Detailed 22-feature documentation with examples | ~50KB | 32 |
| 03 | `03-interpreting-confidence.md` | Confidence interpretation, dual scoring, use cases | ~48KB | 28 |
| 04 | `04-data-schema.md` | Data schema, SQL examples, query patterns | ~42KB | 24 |
| 05 | `05-faq.md` | Frequently asked questions (all audiences) | ~28KB | 16 |
| 06 | `06-example-queries.md` | Natural language query examples with SQL translations | ~35KB | 20 |
| 07 | `07-business-guidelines.md` | Business best practices, workflows, use cases | ~38KB | 22 |
| 08 | `08-troubleshooting.md` | Common issues, errors, performance optimization | ~30KB | 18 |
| 09 | `09-sample-data.md` | 200 real data samples (100 source + 100 predictions) | ~40KB | 25 |
| 10 | `10-glossary.md` | Complete glossary of terms, acronyms, definitions | ~32KB | 20 |
| 11 | `11-quick-start.md` | 5-minute quick start guide for new users | ~26KB | 16 |
| 12 | `12-model-performance.md` | Performance metrics, validation strategy, limitations | ~38KB | 24 |

**Total:** 13 documents, ~479KB, ~288 pages equivalent

---

## Document Relationships

### Primary Documents (Core Knowledge)

**Start Here:**
- `01-model-overview.md` → Understanding what the model does
- `02-features.md` → Understanding how the model works

**Then:**
- `03-interpreting-confidence.md` → Understanding confidence scores
- `04-data-schema.md` → Understanding how to query data

### Secondary Documents (Application Knowledge)

**For Business Users:**
- `07-business-guidelines.md` → How to use predictions for segmentation
- `03-interpreting-confidence.md` → How to interpret confidence scores

**For Technical Users:**
- `04-data-schema.md` → SQL query patterns and data structure
- `06-example-queries.md` → Natural language → SQL examples

**For Troubleshooting:**
- `08-troubleshooting.md` → Common errors and solutions
- `05-faq.md` → Quick answers to common questions

---

## Document Usage by Persona

### Data Scientists / ML Engineers
**Primary:** 01, 02, 04, 12  
**Secondary:** 08  
**Focus:** Model architecture, features, training data, validation

### Marketing / Sales Teams
**Primary:** 03, 07  
**Secondary:** 01, 05, 06  
**Focus:** Age segmentation, targeting, confidence interpretation

### Business Analysts
**Primary:** 04, 06, 07  
**Secondary:** 03, 05  
**Focus:** Query patterns, use cases, data analysis

### Product Teams
**Primary:** 03, 07  
**Secondary:** 01, 04  
**Focus:** Product segmentation, demographic analysis

### Technical Support / IT
**Primary:** 04, 08  
**Secondary:** 05, 06  
**Focus:** Query troubleshooting, access issues, performance optimization

### Bedrock Agent (AI)
**Primary:** 04, 06  
**Secondary:** 01, 02, 03, 05  
**Focus:** Natural language → SQL translation, query examples, feature explanations

---

## Embedding Strategy (for Bedrock Knowledge Base)

### Chunking Configuration

**Recommended Settings:**
- **Chunking Strategy:** Fixed-size
- **Chunk Size:** 1000 tokens (~750 words)
- **Overlap:** 200 tokens (20%)
- **Embedding Model:** amazon.titan-embed-text-v2:0

**Rationale:**
- 1000 tokens balances context (enough detail) with precision (targeted retrieval)
- 200 token overlap prevents loss of context at chunk boundaries
- Titan v2 supports up to 8,192 tokens but smaller chunks = better precision

### Expected Chunk Distribution

| Document | Est. Chunks | Key Chunk Topics |
|----------|-------------|------------------|
| 01-model-overview.md | ~60 | Model architecture, training data, XGBoost, infrastructure |
| 02-features.md | ~50 | 22 features (2-3 chunks each), feature importance |
| 03-interpreting-confidence.md | ~48 | Dual scoring, confidence tiers, margin of error |
| 04-data-schema.md | ~42 | Schema, query patterns (20+ SQL examples) |
| 05-faq.md | ~28 | Q&A pairs (45+ questions) |
| 06-example-queries.md | ~35 | NL→SQL examples (18 query patterns) |
| 07-business-guidelines.md | ~38 | Use cases, segmentation, ROI |
| 08-troubleshooting.md | ~30 | Error solutions, performance tips |

**Total:** ~331 chunks

### Retrieval Performance

**Query Types and Expected Chunks Returned:**

| Query Type | Example | Relevant Docs | Est. Chunks Retrieved |
|------------|---------|---------------|-----------------------|
| Model explanation | "How does age prediction work?" | 01, 02 | 3-5 chunks (architecture, training) |
| Feature explanation | "What features predict age?" | 02 | 2-4 chunks (feature list, descriptions) |
| Confidence interpretation | "What does 85% confidence mean?" | 03 | 2-3 chunks (scoring, interpretation) |
| SQL query | "Show me ages 25-35" | 04, 06 | 2-4 chunks (query patterns, examples) |
| Troubleshooting | "Why negative confidence scores?" | 08 | 2-3 chunks (quantile explanation) |
| Business use | "How to segment by age?" | 07 | 3-5 chunks (use cases, best practices) |

**Typical Retrieval:**
- Bedrock Agent queries KB
- KB returns top 5-10 most relevant chunks (ranked by semantic similarity)
- Agent uses chunks + action group results to formulate response

---

## Maintenance and Updates

### When to Update Documents

**Quarterly (Aligned with Data Updates):**
- `01-model-overview.md` → Update model version, training data period
- `02-features.md` → Update if features change (add/remove/modify)
- `03-interpreting-confidence.md` → Update confidence distributions
- `05-faq.md` → Add new questions from users

**After Model Improvements:**
- `01-model-overview.md` → Add new model performance metrics
- `02-features.md` → Update feature importance rankings
- `07-business-guidelines.md` → Update recommendations based on results
- `12-model-performance.md` → Update validation results

**As Needed:**
- `04-data-schema.md` → Add new query patterns as discovered
- `06-example-queries.md` → Add new NL→SQL examples from user queries
- `08-troubleshooting.md` → Add new error solutions as encountered

### Update Process

1. **Edit Local File:**
   - Update markdown file in `docs/bedrock-agent/kb-source/`
   - Increment version number in header
   - Update "Last Updated" date

2. **Upload to S3:**
   ```bash
   aws s3 cp docs/bedrock-agent/kb-source/01-model-overview.md \
   s3://${S3_BUCKET}/predict-age/agent-context-upload/
   ```

3. **Sync Knowledge Base:**
   - AWS Console → Bedrock → Knowledge Bases → Sync Data Source
   - Or via CLI:
   ```bash
   aws bedrock-agent start-ingestion-job \
   --knowledge-base-id <KB_ID> \
   --data-source-id <DS_ID>
   ```

4. **Verify:**
   - Test query with Bedrock Agent
   - Confirm updated information is returned

**Sync Time:** ~2-3 minutes for 13 files

---

## Quality Checklist

### Before Uploading to S3

- [ ] All markdown files are valid (no syntax errors)
- [ ] All SQL examples are tested and correct
- [ ] All file names follow naming convention (`00-` through `12-`)
- [ ] All headers include version and date
- [ ] All cross-references are correct (e.g., "See `02-features.md`")
- [ ] No placeholder text (e.g., "TODO", "TBD")
- [ ] No dummy data or fake examples
- [ ] All metrics are verified (378M records, 2.23 MAE, etc.)

### After Knowledge Base Sync

- [ ] Test retrieval with sample queries
- [ ] Verify chunk quality (check CloudWatch logs)
- [ ] Test end-to-end with Bedrock Agent
- [ ] Monitor for retrieval errors

---

## Document Statistics

### Token Counts (Approximate)

| Document | Words | Tokens (est.) | Cost (Titan v2) |
|----------|-------|---------------|-----------------|
| 00-knowledge-base-manifest.md | 2,000 | 2,700 | $0.00005 |
| 01-model-overview.md | 8,500 | 11,300 | $0.00023 |
| 02-features.md | 7,000 | 9,300 | $0.00019 |
| 03-interpreting-confidence.md | 6,800 | 9,000 | $0.00018 |
| 04-data-schema.md | 6,000 | 8,000 | $0.00016 |
| 05-faq.md | 4,000 | 5,300 | $0.00011 |
| 06-example-queries.md | 5,000 | 6,600 | $0.00013 |
| 07-business-guidelines.md | 5,500 | 7,300 | $0.00015 |
| 08-troubleshooting.md | 4,200 | 5,600 | $0.00011 |
| 09-sample-data.md | 5,600 | 7,400 | $0.00015 |
| 10-glossary.md | 4,500 | 6,000 | $0.00012 |
| 11-quick-start.md | 3,700 | 4,900 | $0.00010 |
| 12-model-performance.md | 5,300 | 7,000 | $0.00014 |
| **Total** | **68,100** | **90,400** | **$0.00181** |

**One-Time Embedding Cost:** ~$0.0018 (less than 1 penny)  
**Monthly Storage Cost (S3):** ~$0.02  
**Monthly Retrieval Cost:** ~$0 (retrieval is free, only embedding has cost)

---

## Integration with Bedrock Agent

### Knowledge Base Configuration

**Data Source:**
- Type: S3
- S3 URI: `s3://${S3_BUCKET}/predict-age/agent-context-upload/`
- File Format: Markdown (.md)

**Embedding Model:**
- Model: amazon.titan-embed-text-v2:0
- Dimensions: 1024
- Supports: Up to 8,192 tokens per document

**Vector Store:**
- Managed by Bedrock (no OpenSearch Serverless needed)
- Automatic scaling
- Included in Bedrock pricing

### Agent Instructions (Suggested)

```
You are an AI assistant for the Age Prediction Model. Your role is to:

1. Answer questions about the model (how it works, what features are used, accuracy)
2. Help users query age predictions using natural language
3. Explain confidence scores (dual scoring: original + 0-100%)
4. Provide business guidance on using age predictions for segmentation

When answering:
- Be concise and clear
- Cite specific documents when providing technical details
- Translate natural language queries to SQL for data access
- Combine Knowledge Base context with Action Group results
- Always clarify confidence scores (100% = real data, <15 = good ML)

Knowledge Base contains:
- Model documentation (architecture, features, training: 2.23 year MAE)
- Data schema and query examples
- Confidence score interpretation (dual scoring system)
- Business best practices
- Troubleshooting guide
- FAQ
```

### Action Groups (Complement Knowledge Base)

**Action Group 1: query_age_predictions**
- Lambda: Query Athena for age prediction results
- Use when: User asks for data (e.g., "Show me ages 25-35")

**Action Group 2: explain_prediction**
- Lambda: Get feature values for specific PID
- Use when: User asks "Why does PID X have age Y?"

**Action Group 3: compare_segments**
- Lambda: Aggregate statistics by age range
- Use when: User asks "Compare 20s vs 30s demographics"

**Action Group 4: confidence_analysis**
- Lambda: Analyze confidence score distribution
- Use when: User asks "How reliable are the predictions?"

---

## Cost Projection

### One-Time Costs
- **Embedding (Initial):** $0.0018 (less than 1 penny)
- **Knowledge Base Setup:** $0 (no charge for KB creation)

### Monthly Costs (1,000 Queries)
- **S3 Storage (479KB):** $0.02
- **S3 Retrieval (1,000 queries × 5KB avg):** $0.0004
- **Embedding (No updates):** $0
- **Retrieval (No charge):** $0
- **Total KB Cost:** **$0.02/month**

**With Bedrock Agent (Claude Haiku):**
- Agent Invocation: $3-4/month (1,000 queries)
- Lambda Action Groups: $0.20/month
- Athena Queries: $8/month (or $2/month with caching)
- **Total System Cost:** **$5-7/month** (with caching) ✅ Under $10 target!

---

## Version History

| Version | Date | Changes | Updated By |
|---------|------|---------|------------|
| 1.0 | 2025-10-23 | Initial creation - 13 comprehensive documents | AI Agent Dev Team |

**Next Version (1.1 - Planned Q1 2026):**
- Add hyperparameter tuning results
- Add feature engineering improvements
- Add ensemble model comparisons
- Update cost analysis with actual usage data

---

## Document Maintainers

**Primary:** AI Agent Development Team  
**Reviewers:** Data Science Team, Product Analytics Team  
**Contact:** #predict-age (Slack)

---

**Knowledge Base Status:** Ready for Upload and Sync  
**Last Verified:** October 23, 2025  
**Next Review:** January 2026 (post model improvements)

