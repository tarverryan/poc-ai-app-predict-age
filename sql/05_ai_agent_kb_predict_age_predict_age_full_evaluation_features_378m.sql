-- Evaluation Features: 21 features for ALL 378M PIDs
-- Source: staging_parsed_features_2025q3 (pre-parsed JSON fields)
-- Used for batch prediction (898 batches of ~1M records each)
-- NOTE: Replace ${S3_BUCKET} with your actual S3 bucket name before execution

CREATE TABLE ${DATABASE_NAME}.predict_age_full_evaluation_features_378m
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://${S3_BUCKET}/predict-age/predict_age_full_evaluation_features_378m/',
    bucketed_by = ARRAY['batch_id'],
    bucket_count = 898
) AS
SELECT 
    pid,
    
    -- Batch ID for parallel processing (898 batches of ~1M records)
    CAST(FLOOR(ROW_NUMBER() OVER (ORDER BY pid) / 420935.0) AS BIGINT) as batch_id,
    
    -- ==================================================
    -- CAREER STAGE INDICATORS (5 features)
    -- ==================================================
    
    CASE 
        WHEN job_start_date IS NOT NULL THEN
            date_diff('month', date_parse(job_start_date, '%Y-%m-%d'), current_date)
        WHEN job_level = 'C-Team' THEN 120
        WHEN job_level = 'Manager' THEN 60
        ELSE 36
    END as tenure_months,
    
    CASE job_level
        WHEN 'C-Team' THEN 4
        WHEN 'Manager' THEN 3
        WHEN 'Staff' THEN 2
        ELSE 1
    END as job_level_encoded,
    
    CASE 
        WHEN LOWER(job_title) LIKE '%chief%' OR LOWER(job_title) LIKE '%vp%' THEN 5
        WHEN LOWER(job_title) LIKE '%senior%' OR LOWER(job_title) LIKE '%principal%' THEN 4
        WHEN LOWER(job_title) LIKE '%manager%' OR LOWER(job_title) LIKE '%director%' THEN 3
        WHEN LOWER(job_title) LIKE '%associate%' OR LOWER(job_title) LIKE '%analyst%' THEN 2
        WHEN LOWER(job_title) LIKE '%junior%' OR LOWER(job_title) LIKE '%entry%' THEN 1
        ELSE 3
    END as job_seniority_score,
    
    CASE compensation_range
        WHEN '$200,001+' THEN 8
        WHEN '$150,001 - $200,000' THEN 7
        WHEN '$100,001 - $150,000' THEN 6
        WHEN '$75,001 - $100,000' THEN 5
        WHEN '$50,001 - $75,000' THEN 4
        WHEN '$25,001 - $50,000' THEN 3
        ELSE 4
    END as compensation_encoded,
    
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
    
    CASE 
        WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 500 THEN 1.0
        WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 200 THEN 0.8
        WHEN linkedin_connection_count IS NOT NULL AND CAST(linkedin_connection_count AS INT) > 100 THEN 0.6
        ELSE 0.3
    END as linkedin_activity_score,
    
    COALESCE(date_diff('day', date_parse(ev_last_date, '%Y-%m-%d'), current_date), 365) as days_since_profile_update,
    
    CASE 
        WHEN linkedin_url_is_valid = true AND facebook_url IS NOT NULL AND twitter_url IS NOT NULL THEN 1.0
        WHEN linkedin_url_is_valid = true AND (facebook_url IS NOT NULL OR twitter_url IS NOT NULL) THEN 0.7
        WHEN linkedin_url_is_valid = true THEN 0.5
        ELSE 0.2
    END as social_media_presence_score,
    
    CASE 
        WHEN work_email IS NOT NULL AND personal_email IS NOT NULL THEN 1.0
        WHEN work_email IS NOT NULL OR personal_email IS NOT NULL THEN 0.5
        ELSE 0.0
    END as email_engagement_score,
    
    -- ==================================================
    -- INDUSTRY & FUNCTION (3 features)
    -- ==================================================
    
    CASE CAST(industry AS VARCHAR)
        WHEN 'Technology' THEN 35
        WHEN 'Consulting' THEN 38
        WHEN 'Finance' THEN 42
        WHEN 'Healthcare' THEN 45
        WHEN 'Education' THEN 48
        WHEN 'Government' THEN 50
        ELSE 40
    END as industry_typical_age,
    
    CASE CAST(job_function AS VARCHAR)
        WHEN 'Engineering' THEN 1
        WHEN 'Sales' THEN 2
        WHEN 'Marketing' THEN 3
        WHEN 'Finance' THEN 4
        WHEN 'Operations' THEN 5
        ELSE 0
    END as job_function_encoded,
    
    CASE CAST(revenue_range AS VARCHAR)
        WHEN '$1B+' THEN 9
        WHEN '$500M to $1B' THEN 8
        WHEN '$100M to $500M' THEN 7
        ELSE 5
    END as company_revenue_encoded,
    
    -- ==================================================
    -- TEMPORAL (1 feature)
    -- ==================================================
    
    EXTRACT(QUARTER FROM current_date) as quarter,
    
    -- ==================================================
    -- EDUCATION & EXPERIENCE (6 features)
    -- ==================================================
    
    COALESCE(education_level, 2) as education_level_encoded,
    graduation_year,
    COALESCE(number_of_jobs, 1) as number_of_jobs,
    COALESCE(skill_count, 5) as skill_count,
    
    CASE 
        WHEN number_of_jobs IS NOT NULL AND number_of_jobs > 0 THEN
            LEAST(50, GREATEST(1, CAST(tenure_months AS DOUBLE) / 12.0 + (number_of_jobs - 1) * 2.5))
        WHEN graduation_year IS NOT NULL THEN
            2025 - graduation_year
        ELSE 
            CAST(tenure_months AS DOUBLE) / 12.0
    END as total_career_years,
    
    CASE 
        WHEN number_of_jobs IS NOT NULL AND number_of_jobs > 0 
             AND tenure_months IS NOT NULL AND tenure_months > 12 THEN
            CAST(number_of_jobs AS DOUBLE) / (CAST(tenure_months AS DOUBLE) / 12.0)
        ELSE 0.2
    END as job_churn_rate,
    
    -- ==================================================
    -- INTERACTION TERMS (2 features)
    -- ==================================================
    
    tenure_months * CASE job_level
        WHEN 'C-Team' THEN 4
        WHEN 'Manager' THEN 3
        WHEN 'Staff' THEN 2
        ELSE 1
    END as tenure_job_level_interaction,
    
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
WHERE pid IS NOT NULL;

-- Expected output: 378M records with 21 features each, bucketed into 898 batches

