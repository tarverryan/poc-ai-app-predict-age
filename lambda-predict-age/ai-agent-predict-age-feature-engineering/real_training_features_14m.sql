-- NOTE: Replace ${S3_BUCKET} with your actual S3 bucket name before execution
-- This SQL file is used by Lambda functions which will substitute the bucket name from environment variables
CREATE TABLE ${DATABASE_NAME}.predict_age_real_training_features_14m
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://${S3_BUCKET}/predict-age/predict_age_real_training_features_14m/'
) AS
WITH base_features AS (
SELECT
    pid,
    CASE 
        WHEN job_start_date IS NOT NULL AND LENGTH(TRIM(job_start_date)) >= 7 THEN
            date_diff('month',
                date_parse(
                    CASE 
                        WHEN LENGTH(TRIM(job_start_date)) = 7 THEN CONCAT(TRIM(job_start_date), '-01')
                        WHEN LENGTH(TRIM(job_start_date)) >= 10 THEN TRIM(job_start_date)
                        ELSE NULL
                    END,
                    '%Y-%m-%d'
                ),
                current_date
            )
        WHEN job_level = 'C-Team' THEN 120
        WHEN job_level = 'Manager' THEN 60
        ELSE 36
    END as tenure_months,
    job_level,
    job_title,
    compensation_range,
    employee_range,
    linkedin_connection_count,
    ev_last_date,
    linkedin_url_is_valid,
    facebook_url,
    twitter_url,
    work_email,
    personal_email,
    industry,
    job_function,
    revenue_range,
    education_level,
    graduation_year,
    number_of_jobs,
    skill_count,
    birth_year,
    approximate_age
FROM ${DATABASE_NAME}.predict_age_staging_parsed_features_2025q3
WHERE pid IS NOT NULL
  AND MOD(CAST(pid AS BIGINT), 10) = 0  -- 10% sample for training
  AND (birth_year IS NOT NULL OR approximate_age IS NOT NULL)
)
SELECT 
    pid,
    tenure_months,
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
    CASE 
        WHEN linkedin_connection_count IS NOT NULL AND CAST(COALESCE(NULLIF(REGEXP_REPLACE(linkedin_connection_count, '[^0-9]', ''), ''), '0') AS INT) > 500 THEN 1.0
        WHEN linkedin_connection_count IS NOT NULL AND CAST(COALESCE(NULLIF(REGEXP_REPLACE(linkedin_connection_count, '[^0-9]', ''), ''), '0') AS INT) > 200 THEN 0.8
        WHEN linkedin_connection_count IS NOT NULL AND CAST(COALESCE(NULLIF(REGEXP_REPLACE(linkedin_connection_count, '[^0-9]', ''), ''), '0') AS INT) > 100 THEN 0.6
        ELSE 0.3
    END as linkedin_activity_score,
    COALESCE(date_diff('day', 
        date_parse(
            CASE 
                WHEN ev_last_date IS NOT NULL AND LENGTH(TRIM(ev_last_date)) = 7 THEN CONCAT(TRIM(ev_last_date), '-01')
                WHEN ev_last_date IS NOT NULL AND LENGTH(TRIM(ev_last_date)) >= 10 THEN TRIM(ev_last_date)
                ELSE NULL
            END,
            '%Y-%m-%d'
        ), 
        current_date), 365) as days_since_profile_update,
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
    EXTRACT(QUARTER FROM current_date) as quarter,
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
    current_date as feature_creation_date,
    'v1.0_21_features_with_json_parsing' as feature_version
FROM base_features