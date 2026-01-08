-- Training Targets: Actual ages for model training
-- Training set: 10% sample (MOD(id, 10) = 0) = ~14M records
-- Target: actual_age (integer, 18-75 years)
-- NOTE: Replace ${S3_BUCKET} with your actual S3 bucket name before execution
-- This SQL file is used by Lambda functions which will substitute the bucket name from environment variables

CREATE TABLE ${DATABASE_NAME}.predict_age_real_training_targets_14m
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    external_location = 's3://${S3_BUCKET}/predict-age/predict_age_real_training_targets_14m/'
) AS
WITH known_ages AS (
    SELECT 
        id,
        -- Prefer birth_year (more accurate), fallback to approximate_age
        CASE 
            WHEN birth_year IS NOT NULL AND CAST(birth_year AS INT) BETWEEN 1930 AND 2007 
                THEN 2025 - CAST(birth_year AS INT)
            WHEN approximate_age IS NOT NULL AND CAST(approximate_age AS INT) BETWEEN 18 AND 75 
                THEN CAST(approximate_age AS INT)
            ELSE NULL
        END as actual_age,
        birth_year,
        approximate_age
    FROM ${SOURCE_DATABASE}.${SOURCE_TABLE}
    WHERE id IS NOT NULL
      AND (birth_year IS NOT NULL OR approximate_age IS NOT NULL)
      AND MOD(CAST(id AS BIGINT), 10) = 0  -- 10% sample (matches training features)
)
SELECT 
    pid,
    actual_age,
    birth_year,
    approximate_age,
    current_date as target_creation_date,
    'v1.0_real_age_data' as target_version
FROM known_ages
WHERE actual_age IS NOT NULL
  AND actual_age BETWEEN 18 AND 75;  -- Filter outliers

-- Expected output: ~14M records with ages 18-75

