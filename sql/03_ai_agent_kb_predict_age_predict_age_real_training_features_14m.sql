-- Training Features: 21 features for age prediction model
-- Training set: 10% sample (MOD(pid, 10) = 0) = ~14M records
-- Source: staging_parsed_features_2025q3 (pre-parsed JSON fields)
-- NOTE: Replace ${S3_BUCKET} with your actual S3 bucket name before execution

CREATE TABLE ${DATABASE_NAME}.predict_age_real_training_features_14m
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://${S3_BUCKET}/predict-age/predict_age_real_training_features_14m/'
) AS
SELECT 
    pid,
    
    -- ==================================================
    -- CAREER STAGE INDICATORS (5 features)
    -- ==================================================
    
    -- Feature 1: Tenure months (older = longer tenure)
    CASE 
        WHEN job_start_date IS NOT NULL THEN
            date_diff('month', date_parse(job_start_date, '%Y-%m-%d'), current_date)
        WHEN job_level = 'C-Team' THEN 120  -- C-suite avg tenure = 10 years
        WHEN job_level = 'Manager' THEN 60   -- Managers avg = 5 years
        ELSE 36  -- Default = 3 years
    END as tenure_months,
    
    -- Feature 2: Job level encoded (senior = older)
    CASE job_level
        WHEN 'C-Team' THEN 4      -- Avg age 50+
        WHEN 'Manager' THEN 3     -- Avg age 40-50
        WHEN 'Staff' THEN 2       -- Avg age 30-40
        ELSE 1                    -- Avg age 20-30
    END as job_level_encoded,
    
    -- Feature 3: Job seniority score (title keywords)
    CASE 
        WHEN LOWER(job_title) LIKE '%chief%' OR LOWER(job_title) LIKE '%vp%' THEN 5
        WHEN LOWER(job_title) LIKE '%senior%' OR LOWER(job_title) LIKE '%principal%' THEN 4
        WHEN LOWER(job_title) LIKE '%manager%' OR LOWER(job_title) LIKE '%director%' THEN 3
        WHEN LOWER(job_title) LIKE '%associate%' OR LOWER(job_title) LIKE '%analyst%' THEN 2
        WHEN LOWER(job_title) LIKE '%junior%' OR LOWER(job_title) LIKE '%entry%' THEN 1
        ELSE 3
    END as job_seniority_score,
    
    -- Feature 4: Compensation encoded (higher = older/experienced)
    CASE compensation_range
        WHEN '$200,001+' THEN 8
        WHEN '$150,001 - $200,000' THEN 7
        WHEN '$100,001 - $150,000' THEN 6
        WHEN '$75,001 - $100,000' THEN 5
        WHEN '$50,001 - $75,000' THEN 4
        WHEN '$25,001 - $50,000' THEN 3
        ELSE 4  -- Default moderate compensation
    END as compensation_encoded,
    
    -- Feature 5: Company size encoded (larger = older workforce avg)
    CASE CAST(employee_range AS VARCHAR)
        WHEN '10000+' THEN 9
        WHEN '5000 to 9999' THEN 8
        WHEN '1000 to 4999' THEN 7
        WHEN '500 to 999' THEN 6
        WHEN '200 to 499' THEN 5
        ELSE 4
    END as company_size_encoded,
    
    -- ==================================================
    -- DIGITAL FOOTPRINT (4 features)
    -- ==================================================
    
    -- Feature 6: LinkedIn activity score (younger = more active)
    CASE 
        WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 500 THEN 1.0
        WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 200 THEN 0.8
        WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 100 THEN 0.6
        ELSE 0.3
    END as linkedin_activity_score,
    
    -- Feature 7: Days since profile update (younger = more recent)
    COALESCE(date_diff('day', date_parse(ev_last_date, '%Y-%m-%d'), current_date), 365) as days_since_profile_update,
    
    -- Feature 8: Social media presence score (younger = more platforms)
    CASE 
        WHEN linkedin_url_is_valid = true AND facebook_url IS NOT NULL AND twitter_url IS NOT NULL THEN 1.0
        WHEN linkedin_url_is_valid = true AND (facebook_url IS NOT NULL OR twitter_url IS NOT NULL) THEN 0.7
        WHEN linkedin_url_is_valid = true THEN 0.5
        ELSE 0.2
    END as social_media_presence_score,
    
    -- Feature 9: Email engagement (work + personal)
    CASE 
        WHEN work_email IS NOT NULL AND personal_email IS NOT NULL THEN 1.0
        WHEN work_email IS NOT NULL OR personal_email IS NOT NULL THEN 0.5
        ELSE 0.0
    END as email_engagement_score,
    
    -- ==================================================
    -- INDUSTRY & FUNCTION (3 features)
    -- ==================================================
    
    -- Feature 10: Industry typical age
    CASE CAST(industry AS VARCHAR)
        WHEN 'Technology' THEN 35         -- Younger workforce
        WHEN 'Consulting' THEN 38
        WHEN 'Finance' THEN 42
        WHEN 'Healthcare' THEN 45
        WHEN 'Education' THEN 48
        WHEN 'Government' THEN 50         -- Older workforce
        ELSE 40
    END as industry_typical_age,
    
    -- Feature 11: Job function encoded
    CASE CAST(job_function AS VARCHAR)
        WHEN 'Engineering' THEN 1
        WHEN 'Sales' THEN 2
        WHEN 'Marketing' THEN 3
        WHEN 'Finance' THEN 4
        WHEN 'Operations' THEN 5
        ELSE 0
    END as job_function_encoded,
    
    -- Feature 12: Company revenue encoded (proxy for maturity)
    CASE CAST(revenue_range AS VARCHAR)
        WHEN '$1B+' THEN 9
        WHEN '$500M to $1B' THEN 8
        WHEN '$100M to $500M' THEN 7
        ELSE 5
    END as company_revenue_encoded,
    
    -- ==================================================
    -- TEMPORAL (1 feature)
    -- ==================================================
    
    -- Feature 13: Quarter (seasonality patterns)
    EXTRACT(QUARTER FROM current_date) as quarter,
    
    -- ==================================================
    -- EDUCATION & EXPERIENCE (6 features) ⭐ NEW!
    -- ==================================================
    
    -- Feature 14: Education level (parsed from JSON)
    COALESCE(education_level, 2) as education_level_encoded,
    
    -- Feature 15: Graduation year (validation signal)
    graduation_year,
    
    -- Feature 16: Number of jobs (career history)
    COALESCE(number_of_jobs, 1) as number_of_jobs,
    
    -- Feature 17: Skill count (experience proxy)
    COALESCE(skill_count, 5) as skill_count,
    
    -- Feature 18: Total career years (STRONGEST PREDICTOR!)
    CASE 
        WHEN number_of_jobs IS NOT NULL AND number_of_jobs > 0 THEN
            -- Estimate: 22 years old at first job + (tenure + gaps)
            -- Approximate as: age_at_first_job + (number_of_jobs * avg_job_duration)
            LEAST(50, GREATEST(1, CAST(tenure_months AS DOUBLE) / 12.0 + (number_of_jobs - 1) * 2.5))
        WHEN graduation_year IS NOT NULL THEN
            -- If we have graduation year, calculate years since graduation
            2025 - graduation_year
        ELSE 
            -- Fallback to tenure
            CAST(tenure_months AS DOUBLE) / 12.0
    END as total_career_years,
    
    -- Feature 19: Job churn rate (jobs per year of career)
    CASE 
        WHEN number_of_jobs IS NOT NULL AND number_of_jobs > 0 
             AND tenure_months IS NOT NULL AND tenure_months > 12 THEN
            CAST(number_of_jobs AS DOUBLE) / (CAST(tenure_months AS DOUBLE) / 12.0)
        ELSE 0.2  -- Default moderate churn
    END as job_churn_rate,
    
    -- ==================================================
    -- INTERACTION TERMS (2 features)
    -- ==================================================
    
    -- Feature 20: Tenure × Job Level (senior + long tenure = older)
    tenure_months * CASE job_level
        WHEN 'C-Team' THEN 4
        WHEN 'Manager' THEN 3
        WHEN 'Staff' THEN 2
        ELSE 1
    END as tenure_job_level_interaction,
    
    -- Feature 21: Compensation × Company Size (high comp at large company = older)
    (CASE compensation_range
        WHEN '$200,001+' THEN 8
        WHEN '$150,001 - $200,000' THEN 7
        WHEN '$100,001 - $150,000' THEN 6
        WHEN '$75,001 - $100,000' THEN 5
        WHEN '$50,001 - $75,000' THEN 4
        WHEN '$25,001 - $50,000' THEN 3
        ELSE 4
    END) * (CASE CAST(employee_range AS VARCHAR)
        WHEN '10000+' THEN 9
        WHEN '5000 to 9999' THEN 8
        WHEN '1000 to 4999' THEN 7
        WHEN '500 to 999' THEN 6
        WHEN '200 to 499' THEN 5
        ELSE 4
    END) as comp_size_interaction,
    
    -- Metadata
    current_date as feature_creation_date,
    'v1.0_21_features_with_json_parsing' as feature_version

FROM ${DATABASE_NAME}.predict_age_staging_parsed_features_2025q3
WHERE pid IS NOT NULL
  AND MOD(CAST(pid AS BIGINT), 10) = 0  -- 10% sample for training
  AND (birth_year IS NOT NULL OR approximate_age IS NOT NULL);  -- Must have age data

-- Expected output: ~14M records with 21 features each

