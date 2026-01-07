# Age Prediction Features - Complete Reference

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Applies To:** Model v1.0_xgboost

---

## Overview

The Age Prediction Model uses **22 career and demographic features** to predict employee/contact ages. These features are automatically extracted from profile data and encoded for machine learning.

**Feature Categories:**
1. **Career Tenure** (3 features) - Time in role and company
2. **Digital Footprint** (2 features) - LinkedIn and social presence
3. **Job Characteristics** (5 features) - Level, function, industry
4. **Profile Richness** (5 features) - Education, skills, experience
5. **Compensation Indicators** (2 features) - Salary signals
6. **Engagement Metrics** (3 features) - Activity and interaction
7. **Derived Features** (2 features) - Computed from other fields

---

## Feature Importance Ranking

Based on XGBoost feature importance scores:

| Rank | Feature | Importance | Category | Predictive Power |
|------|---------|------------|----------|------------------|
| 1 | **total_career_years** | 0.234 | Derived | ⭐⭐⭐⭐⭐ Strongest |
| 2 | tenure_months | 0.156 | Career Tenure | ⭐⭐⭐⭐⭐ |
| 3 | job_level_encoded | 0.128 | Job Characteristics | ⭐⭐⭐⭐ |
| 4 | education_level_encoded | 0.097 | Profile Richness | ⭐⭐⭐⭐ |
| 5 | work_experience_count | 0.083 | Profile Richness | ⭐⭐⭐ |
| 6 | company_size_encoded | 0.071 | Job Characteristics | ⭐⭐⭐ |
| 7 | linkedin_connection_count | 0.064 | Digital Footprint | ⭐⭐⭐ |
| 8 | skills_count | 0.052 | Profile Richness | ⭐⭐ |
| 9 | job_function_encoded | 0.041 | Job Characteristics | ⭐⭐ |
| 10 | industry_turnover_rate | 0.037 | Job Characteristics | ⭐⭐ |
| ... | (12 more features) | <0.035 | Various | ⭐ |

**Top 5 features account for 69.8% of predictive power.**

---

## Detailed Feature Descriptions

### 1. Career Tenure Features

#### 1.1 tenure_months
**Definition:** Number of months in current role/company  
**Type:** Numeric (0-600)  
**Encoding:** Raw value, no transformation  
**Coverage:** 92% of PIDs

**Interpretation:**
- **0-12 months:** Early career or job hopper → Age 22-28
- **13-60 months:** Mid-career stable → Age 28-40
- **61-180 months:** Senior/established → Age 35-50
- **180+ months:** Very senior/lifetime → Age 45-65

**Example:**
```
tenure_months = 84 (7 years)
→ Likely age range: 32-42
→ Strong signal of career establishment
```

**Missing Value Handling:** Impute with median (36 months)

---

#### 1.2 company_tenure_years
**Definition:** Years at current company (derived from start date)  
**Type:** Numeric (0-50)  
**Encoding:** Raw value  
**Coverage:** 78% of PIDs

**Interpretation:**
- **0-2 years:** New employee or contractor → Age varies
- **3-7 years:** Established employee → Age 28-45
- **8-15 years:** Long-term employee → Age 35-55
- **15+ years:** Very long tenure → Age 40-65

**Correlation:** High correlation with tenure_months (0.85)

---

#### 1.3 time_since_last_promotion_months
**Definition:** Months since last job title change  
**Type:** Numeric (0-360)  
**Encoding:** Raw value  
**Coverage:** 45% of PIDs

**Interpretation:**
- **0-18 months:** Recent promotion → Age-agnostic (all ages)
- **19-60 months:** Stable period → Typical 3-5 year cycle
- **60+ months:** Stagnant or at career peak → Age 40+

**Missing Value Handling:** Impute with -1 (unknown)

---

### 2. Digital Footprint Features

#### 2.1 linkedin_connection_count
**Definition:** Number of LinkedIn connections  
**Type:** Numeric (0-30,000)  
**Encoding:** Log-transformed: log(count + 1)  
**Coverage:** 67% of PIDs

**Interpretation:**
- **0-100:** Early career or private → Age 22-28
- **101-500:** Established professional → Age 28-40
- **501-1,500:** Well-networked → Age 35-50
- **1,500+:** Executive/influencer → Age 40-60

**Example:**
```
linkedin_connection_count = 847
→ log(847 + 1) = 6.74
→ Likely age range: 35-45
→ Well-established professional
```

**Missing Value Handling:** Impute with median (500)

**Why Log Transform?**
Connection count is highly skewed (most have <500, some have 10,000+). Log transform normalizes the distribution for ML.

---

#### 2.2 social_media_activity_score
**Definition:** Composite score of social media presence (Twitter, GitHub, etc.)  
**Type:** Numeric (0.0-1.0)  
**Encoding:** Pre-computed score  
**Coverage:** 38% of PIDs

**Interpretation:**
- **0.0-0.2:** Minimal online presence → Age varies
- **0.3-0.6:** Moderate activity → Age 25-40
- **0.7-1.0:** Very active → Age 25-35 (younger skew)

**Missing Value Handling:** Impute with 0.0 (no activity)

---

### 3. Job Characteristics Features

#### 3.1 job_level_encoded
**Definition:** Seniority level (Entry, Mid, Senior, Executive)  
**Type:** Ordinal (1-10)  
**Encoding:** Manual mapping:
```
Entry/Junior → 1-3
Mid/Intermediate → 4-6
Senior/Lead → 7-8
Manager/Director → 9
VP/C-Level → 10
```
**Coverage:** 89% of PIDs

**Interpretation:**
- **1-3 (Entry):** Age 22-28
- **4-6 (Mid):** Age 28-38
- **7-8 (Senior):** Age 35-50
- **9 (Manager):** Age 38-55
- **10 (Executive):** Age 45-65

**Example:**
```
job_level_encoded = 7 (Senior)
→ Likely age range: 35-50
→ Strong signal of career progression
```

**Missing Value Handling:** Impute with 5 (mid-level)

---

#### 3.2 job_function_encoded
**Definition:** Job function category (Engineering, Sales, HR, etc.)  
**Type:** Ordinal (1-12)  
**Encoding:** Frequency-based encoding (most common = 1)  
**Coverage:** 91% of PIDs

**Interpretation:**
Different functions have different age profiles:
- **Engineering/Tech:** Younger skew (avg age 33)
- **Sales/Marketing:** Mid-career (avg age 36)
- **Executive/Leadership:** Older skew (avg age 48)

**Missing Value Handling:** Impute with 6 (median function)

---

#### 3.3 industry_type_encoded
**Definition:** Industry sector (Tech, Healthcare, Finance, etc.)  
**Type:** Ordinal (1-15)  
**Encoding:** Industry average age ranking  
**Coverage:** 87% of PIDs

**Interpretation:**
- **Tech/Startup:** Younger (avg age 32)
- **Finance/Consulting:** Mid-career (avg age 37)
- **Government/Education:** Older (avg age 42)

---

#### 3.4 company_size_encoded
**Definition:** Employee count at company  
**Type:** Ordinal (1-10)  
**Encoding:** Bucketed ranges:
```
1 = 1-10 employees
2 = 11-50
3 = 51-200
4 = 201-500
5 = 501-1,000
6 = 1,001-5,000
7 = 5,001-10,000
8 = 10,001-50,000
9 = 50,001-100,000
10 = 100,000+
```
**Coverage:** 84% of PIDs

**Interpretation:**
- **1-3 (Small):** Varied ages, startup skew younger
- **4-7 (Medium):** Mid-career concentration (30-45)
- **8-10 (Large):** Wider age range, more older workers

---

#### 3.5 industry_turnover_rate
**Definition:** Average turnover rate for employee's industry  
**Type:** Numeric (0.05-0.45)  
**Encoding:** Pre-computed industry average  
**Coverage:** 87% of PIDs

**Interpretation:**
- **High turnover (>0.30):** Retail, hospitality → Younger workforce
- **Medium turnover (0.15-0.30):** Tech, consulting → Mixed ages
- **Low turnover (<0.15):** Government, education → Older workforce

---

### 4. Profile Richness Features

#### 4.1 education_level_encoded
**Definition:** Highest education level completed  
**Type:** Ordinal (1-7)  
**Encoding:**
```
1 = High School
2 = Some College
3 = Associate's
4 = Bachelor's
5 = Master's
6 = PhD
7 = Professional (JD, MD)
```
**Coverage:** 71% of PIDs

**Interpretation:**
- **1-2 (HS/Some College):** Age varies widely
- **3-4 (Associate's/Bachelor's):** Age 22+
- **5 (Master's):** Age 24+ (2 extra years)
- **6-7 (PhD/Professional):** Age 28+ (5-8 extra years)

**Example:**
```
education_level_encoded = 6 (PhD)
→ Minimum age: 28 (typical PhD completion)
→ Likely age range: 32-55
```

**Missing Value Handling:** Impute with 4 (Bachelor's - most common)

---

#### 4.2 skills_count
**Definition:** Number of skills listed on profile  
**Type:** Numeric (0-200)  
**Encoding:** Capped at 100, then normalized  
**Coverage:** 62% of PIDs

**Interpretation:**
- **0-10 skills:** Early career or sparse profile → Age 22-30
- **11-30 skills:** Mid-career → Age 28-40
- **31-50 skills:** Experienced → Age 35-50
- **50+ skills:** Very experienced or over-reporter → Age 40+

**Missing Value Handling:** Impute with 15 (median)

---

#### 4.3 work_experience_count
**Definition:** Number of previous jobs listed  
**Type:** Numeric (0-30)  
**Encoding:** Raw value  
**Coverage:** 68% of PIDs

**Interpretation:**
- **0-1 jobs:** First or second job → Age 22-28
- **2-4 jobs:** Normal career progression → Age 28-38
- **5-8 jobs:** Experienced or job hopper → Age 35-50
- **9+ jobs:** Very experienced or unstable → Age 40+

**Rule of Thumb:** Average 1 job per 3-5 years of career

**Example:**
```
work_experience_count = 6 jobs
→ Estimated 18-30 years of career
→ Likely age range: 40-52
```

---

#### 4.4 certifications_count
**Definition:** Number of professional certifications  
**Type:** Numeric (0-20)  
**Encoding:** Raw value  
**Coverage:** 28% of PIDs

**Interpretation:**
- **0 certs:** Age-agnostic (all ages)
- **1-3 certs:** Mid-career professionals → Age 30-45
- **4+ certs:** Specialized/senior → Age 35-55

---

#### 4.5 publications_count
**Definition:** Number of publications, patents, papers  
**Type:** Numeric (0-100)  
**Encoding:** Log-transformed  
**Coverage:** 12% of PIDs

**Interpretation:**
- **1-5 pubs:** Early research career → Age 28-35
- **6-20 pubs:** Established researcher → Age 35-50
- **20+ pubs:** Senior researcher → Age 45+

---

### 5. Compensation Indicators

#### 5.1 compensation_range_encoded
**Definition:** Salary range estimate  
**Type:** Ordinal (1-9)  
**Encoding:** Bucketed salary ranges  
**Coverage:** 52% of PIDs

**Interpretation:**
- **1-3 (Low):** Entry-level → Age 22-30
- **4-6 (Medium):** Mid-career → Age 30-45
- **7-9 (High):** Senior/executive → Age 40-60

**Correlation with Age:** 0.52 (moderate positive)

---

#### 5.2 stock_options_indicator
**Definition:** Binary flag for equity compensation  
**Type:** Binary (0/1)  
**Encoding:** 0 = No, 1 = Yes  
**Coverage:** 34% of PIDs

**Interpretation:**
- **0 (No equity):** Age-agnostic
- **1 (Has equity):** Slightly higher age (avg +3 years)

---

### 6. Engagement Metrics

#### 6.1 profile_completeness_score
**Definition:** Percentage of profile fields filled (0-100%)  
**Type:** Numeric (0.0-1.0)  
**Encoding:** Pre-computed percentage  
**Coverage:** 100% of PIDs

**Interpretation:**
- **0.0-0.3:** Sparse profile → Age varies, often younger
- **0.4-0.7:** Normal profile → Age 25-45
- **0.8-1.0:** Very complete → Age 30-50 (career invested)

---

#### 6.2 last_activity_days_ago
**Definition:** Days since last profile update  
**Type:** Numeric (0-3,650)  
**Encoding:** Log-transformed  
**Coverage:** 76% of PIDs

**Interpretation:**
- **0-30 days:** Active profile → Slightly younger skew
- **31-180 days:** Normal activity → Age-neutral
- **180+ days:** Inactive → Slightly older skew

---

#### 6.3 endorsements_count
**Definition:** Number of skill endorsements received  
**Type:** Numeric (0-500)  
**Encoding:** Log-transformed  
**Coverage:** 48% of PIDs

**Interpretation:**
- **0-10:** Limited network → Age 22-30
- **11-50:** Normal engagement → Age 28-40
- **50+:** Well-connected → Age 35+

---

### 7. Derived Features

#### 7.1 total_career_years
**Definition:** Estimated total years of career experience  
**Type:** Numeric (0-50)  
**Calculation:**
```python
total_career_years = (
    work_experience_count * 3.5  # Avg 3.5 years per job
    + tenure_months / 12          # Add current tenure
    + (education_level_encoded - 4) * 2  # Extra years for advanced degrees
)
```
**Coverage:** 94% of PIDs (computed from other features)

**Interpretation:**
- **0-5 years:** Early career → Age 22-28
- **6-10 years:** Early-mid career → Age 28-35
- **11-20 years:** Mid-career → Age 33-45
- **21-30 years:** Senior → Age 43-55
- **30+ years:** Very senior → Age 50+

**This is the STRONGEST predictor of age (importance = 0.234)**

**Example:**
```
work_experience_count = 5 jobs
tenure_months = 48 months (4 years)
education_level_encoded = 5 (Master's)

total_career_years = 5 * 3.5 + 4 + (5-4)*2
                   = 17.5 + 4 + 2
                   = 23.5 years

Predicted age ≈ 22 (start) + 23.5 = 45.5 years
```

---

#### 7.2 career_acceleration_rate
**Definition:** Career progression speed (promotions per year)  
**Type:** Numeric (0.0-1.0)  
**Calculation:**
```python
if total_career_years > 0:
    career_acceleration_rate = job_level_encoded / total_career_years
else:
    career_acceleration_rate = 0
```
**Coverage:** 90% of PIDs

**Interpretation:**
- **<0.3:** Slow progression → Older for level
- **0.3-0.5:** Normal progression → Age aligns with level
- **>0.5:** Fast progression → Younger for level (high performer)

---

## Feature Interactions

### Important Two-Way Interactions

**1. tenure_months × job_level_encoded**
- Long tenure + Low level → Older (plateaued career)
- Short tenure + High level → Younger (fast riser)

**2. total_career_years × education_level_encoded**
- Many years + Low education → Older (experience-based)
- Fewer years + High education → Younger (education-based)

**3. company_size_encoded × job_function_encoded**
- Large company + Executive → Older (50+)
- Small company + Technical → Younger (30s)

---

## Missing Value Strategy

| Feature | Missing % | Imputation Strategy |
|---------|-----------|---------------------|
| High coverage (>80%) | <20% | Median/mode |
| Medium coverage (50-80%) | 20-50% | Median + indicator flag |
| Low coverage (<50%) | >50% | Domain default + indicator flag |

**Example:**
```python
linkedin_connection_count_missing = (linkedin_connection_count == 0)
linkedin_connection_count_imputed = coalesce(linkedin_connection_count, 500)
```

---

## Feature Engineering Process

### 1. Raw Data Extraction
```sql
SELECT 
    pid,
    tenure_months,
    json_extract_scalar(profile_json, '$.linkedin.connections') as linkedin_connections,
    json_extract_scalar(profile_json, '$.education[0].degree') as education_level,
    ...
FROM predict_age_training_raw_14m
```

### 2. Feature Transformation
```python
# Example transformations
df['linkedin_connection_count_log'] = np.log(df['linkedin_connection_count'] + 1)
df['total_career_years'] = calculate_career_years(df)
df['job_level_encoded'] = encode_job_level(df['job_title'])
```

### 3. Validation
- Check feature distributions
- Detect outliers (e.g., tenure_months > 600)
- Verify correlations (detect multicollinearity)

---

## Feature Monitoring

### Quality Metrics
- **Coverage:** % of PIDs with non-null values
- **Distribution:** Check for drift over time
- **Correlation:** Monitor feature-target correlation

### Alerts
- Coverage drops >10% → Investigate data source
- Distribution shifts (KS test) → Consider retraining
- New feature values (e.g., new job level) → Update encoding

---

## Future Feature Additions

### Planned (Q1 2026)
- Career gap years (employment gaps)
- Industry experience years (time in same industry)
- Geographic location (city/region age demographics)
- Company tenure at multiple companies

### Exploratory
- Text features from job descriptions
- Social media text analysis (bio, posts)
- Network features (connections' average age)
- Time-series features (profile update frequency)

---

## Feature Documentation

**Full Feature List:** 22 features  
**Training Coverage:** 94% of PIDs have ≥15 features  
**Prediction Coverage:** 378M PIDs scored  
**Model Type:** XGBoost handles missing values internally

**For More Details:**
- Feature importance analysis: `12-model-performance.md`
- SQL feature extraction: `04-data-schema.md`
- Troubleshooting: `08-troubleshooting.md`

