-- Create database for age prediction project
-- Database: Configure via ${DATABASE_NAME} environment variable (default: ml_predict_age)
-- NOTE: Replace ${S3_BUCKET} with your actual S3 bucket name before execution
-- S3 Path: s3://${S3_BUCKET}/predict-age/
-- Athena Results: s3://${S3_BUCKET}/athena-results/

-- NOTE: Replace ${DATABASE_NAME} with your actual database name before execution
-- This SQL file is used by Lambda functions which will substitute the database name from environment variables
CREATE DATABASE IF NOT EXISTS ${DATABASE_NAME}
COMMENT 'Age prediction ML pipeline - training and evaluation'
LOCATION 's3://${S3_BUCKET}/predict-age/';

