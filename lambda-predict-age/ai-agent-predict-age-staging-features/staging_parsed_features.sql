-- Staging table: Parse JSON fields from source data
-- Extracts education level, career years, job count, skills from JSON
-- This is a one-time parse to avoid repeated JSON operations
-- NOTE: Replace ${S3_BUCKET} with your actual S3 bucket name before execution
-- This SQL file is used by Lambda functions which will substitute the bucket name from environment variables

CREATE TABLE ${DATABASE_NAME}.predict_age_staging_parsed_features_2025q3
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://${S3_BUCKET}/predict-age/predict_age_staging_parsed_features_2025q3/'
) AS
SELECT
    pid,

    -- Original fields (pass through)
    job_title,
    job_level,
    job_function,
    org_name,
    employee_range,
    revenue_range,
    industry,
    linkedin_connection_count,
    linkedin_url_is_valid,
    work_email,
    personal_email,
    job_start_date,
    ev_last_date,
    compensation_range,
    birth_year,
    approximate_age,
    facebook_url,
    twitter_url,

    -- PARSED: Education level from JSON (simplified: search entire string)
    CASE
        WHEN education IS NOT NULL AND education != '' AND education != '[]' THEN
            CASE
                -- Check for PhD/Doctorate
                WHEN LOWER(education) LIKE '%phd%'
                  OR LOWER(education) LIKE '%doctorate%'
                  OR LOWER(education) LIKE '%doctor of%' THEN 5
                -- Check for Master's/MBA
                WHEN LOWER(education) LIKE '%master%'
                  OR LOWER(education) LIKE '%mba%'
                  OR LOWER(education) LIKE '%m.s.%'
                  OR LOWER(education) LIKE '%m.a.%' THEN 4
                -- Check for Bachelor's
                WHEN LOWER(education) LIKE '%bachelor%'
                  OR LOWER(education) LIKE '%b.s.%'
                  OR LOWER(education) LIKE '%b.a.%' THEN 3
                -- Check for Associate's
                WHEN LOWER(education) LIKE '%associate%' THEN 2
                -- Check for High School
                WHEN LOWER(education) LIKE '%high school%' THEN 1
                ELSE 2  -- Default to some college
            END
        ELSE 2  -- Default if no education data
    END as education_level,

    -- PARSED: Latest graduation year from JSON
    TRY(CAST(json_extract_scalar(json_parse(education), '$[0].end_date') AS INT)) as graduation_year,

    -- PARSED: Number of work experiences from JSON array length
    COALESCE(TRY(CAST(json_array_length(json_parse(work_experience)) AS INT)), 0) as number_of_jobs,

    -- PARSED: Skill count from JSON array length
    COALESCE(TRY(CAST(json_array_length(json_parse(skills)) AS INT)), 0) as skill_count,

    -- PARSED: Earliest work start year from JSON
    TRY(YEAR(
        date_parse(
            json_extract_scalar(
                json_parse(work_experience),
                '$[0].start_date'
            ),
            '%Y-%m-%d'
        )
    )) as earliest_work_start_year

FROM ${SOURCE_DATABASE}.${SOURCE_TABLE}
WHERE pid IS NOT NULL;

