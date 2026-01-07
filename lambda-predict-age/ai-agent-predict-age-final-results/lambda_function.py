import json
import boto3
import logging
import os
import time
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
athena_client = boto3.client('athena')
s3_client = boto3.client('s3')

# Configuration
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'ml_predict_age')
S3_BUCKET = os.environ.get('S3_BUCKET')
FINAL_RESULTS_TABLE = 'predict_age_final_results_2025q3'

if not S3_BUCKET:
    raise ValueError("S3_BUCKET environment variable is required")

def execute_athena_query(query, description):
    """Execute Athena query and return execution ID"""
    try:
        logger.info(f"Executing query: {description}")
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': DATABASE_NAME},
            ResultConfiguration={'OutputLocation': f's3://{S3_BUCKET}/athena-results/'},
            WorkGroup='primary'
        )
        execution_id = response['QueryExecutionId']
        logger.info(f"Query started with execution ID: {execution_id}")
        return execution_id
    except Exception as e:
        logger.error(f"Error executing Athena query: {str(e)}")
        raise

def wait_for_query_completion(execution_id):
    """Wait for Athena query to complete"""
    try:
        while True:
            response = athena_client.get_query_execution(QueryExecutionId=execution_id)
            status = response['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                logger.info(f"Query {execution_id} completed successfully")
                break
            elif status == 'FAILED':
                error_reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                logger.error(f"Query {execution_id} failed: {error_reason}")
                raise Exception(f"Athena query failed: {error_reason}")
            elif status == 'CANCELLED':
                logger.error(f"Query {execution_id} was cancelled")
                raise Exception("Athena query was cancelled")
            
            logger.info(f"Query {execution_id} status: {status}. Waiting...")
            time.sleep(10)
            
    except Exception as e:
        logger.error(f"Error waiting for query completion: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Create final results table with 1:1 mapping to source (378M PIDs).
    Combines Human QA predictions with default predictions for missing data.
    Default: Age: 35, Confidence: 15.0 (high uncertainty)
    """
    try:
        # Allow source table to be configurable for testing (use RAW table by default)
        source_table = event.get('source_table', f'{DATABASE_NAME}.predict_age_full_evaluation_raw_378m')
        logger.info(f"Creating final results table: {FINAL_RESULTS_TABLE} from {source_table}")
        
        # Drop existing table
        drop_query = f"DROP TABLE IF EXISTS {DATABASE_NAME}.{FINAL_RESULTS_TABLE}"
        drop_execution_id = execute_athena_query(drop_query, f"Dropping existing table {FINAL_RESULTS_TABLE}")
        wait_for_query_completion(drop_execution_id)
        logger.info(f"Existing table {FINAL_RESULTS_TABLE} dropped (if it existed).")
        
        # Clean up S3 directory
        prefix = f'predict-age/final-results/{FINAL_RESULTS_TABLE}/'
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
            delete_keys = []
            for page in pages:
                if 'Contents' in page:
                    delete_keys.extend([{'Key': obj['Key']} for obj in page['Contents']])
            if delete_keys:
                s3_client.delete_objects(Bucket=S3_BUCKET, Delete={'Objects': delete_keys})
                logger.info(f"Cleaned up {len(delete_keys)} S3 objects from {prefix}")
        except Exception as e:
            logger.warning(f"Error cleaning S3 prefix {prefix}: {str(e)}")
        
        # Create final results table: Existing ages > ML predictions > Defaults
        # Priority: 1) Known age from birth_year/approximate_age, 2) ML prediction, 3) Default (35)
        query = f"""
        CREATE TABLE {DATABASE_NAME}.{FINAL_RESULTS_TABLE}
        WITH (
            external_location = 's3://{S3_BUCKET}/predict-age/final-results/{FINAL_RESULTS_TABLE}/',
            format = 'PARQUET',
            parquet_compression = 'SNAPPY'
        ) AS
        SELECT 
            s.pid,
            COALESCE(
                CAST(s.approximate_age AS INTEGER),          -- Priority 1: Existing approximate_age
                (2025 - CAST(s.birth_year AS INTEGER)),      -- Priority 2: Calculate from birth_year
                pred.predicted_age,                          -- Priority 3: ML prediction
                35                                           -- Priority 4: Default
            ) as predicted_age,
            CASE 
                WHEN s.birth_year IS NOT NULL THEN 100.0         -- Existing birth year (CERTAIN - real data)
                WHEN s.approximate_age IS NOT NULL THEN 100.0    -- Existing approximate age (CERTAIN - real data)
                WHEN pred.pid IS NOT NULL THEN pred.confidence_score  -- ML prediction confidence (varies)
                ELSE 15.0                                        -- Default for missing data
            END as confidence_score,
            CAST(current_timestamp AS VARCHAR) as qa_timestamp,
            COALESCE(
                pred.model_version,
                CASE
                    WHEN s.approximate_age IS NOT NULL THEN 'v1.0_existing_approx_age'
                    WHEN s.birth_year IS NOT NULL THEN 'v1.0_existing_birth_year'
                    ELSE 'v1.0_default_rule'
                END
            ) as model_version,
            CASE 
                WHEN pred.pid IS NOT NULL THEN pred.prediction_status  -- ML prediction status
                WHEN s.approximate_age IS NOT NULL OR s.birth_year IS NOT NULL THEN 'EXISTING_AGE'
                ELSE 'INSUFFICIENT_DATA'
            END as prediction_status,
            CASE
                WHEN s.approximate_age IS NOT NULL THEN 'EXISTING_APPROX_AGE'
                WHEN s.birth_year IS NOT NULL THEN 'EXISTING_BIRTH_YEAR'
                WHEN pred.pid IS NOT NULL THEN 'ML_PREDICTION'
                ELSE 'DEFAULT_RULE'
            END as prediction_source
        FROM (
            -- All PIDs from source table with existing age data
            SELECT 
                CAST(pid AS BIGINT) as pid,
                birth_year,
                approximate_age
            FROM {source_table}
            WHERE pid IS NOT NULL
        ) s
        LEFT JOIN {DATABASE_NAME}.predict_age_human_qa_2025q3 pred
        ON s.pid = pred.pid
        """
        
        execution_id = execute_athena_query(query, f"Creating final results table with defaults")
        wait_for_query_completion(execution_id)
        
        logger.info(f"Final results table {FINAL_RESULTS_TABLE} created successfully!")
        logger.info(f"Table includes:")
        logger.info(f"  • All PIDs (1:1 with source)")
        logger.info(f"  • Existing ages from birth_year/approximate_age (where available)")
        logger.info(f"  • ML predictions for PIDs with missing age data")
        logger.info(f"  • Default age (35) for PIDs with no data and no prediction")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Final results table {FINAL_RESULTS_TABLE} created successfully with 1:1 mapping!',
                'table_name': FINAL_RESULTS_TABLE,
                'execution_id': execution_id,
                'timestamp': datetime.now().isoformat(),
                'expected_records': 378024173,
                'default_age': 35,
                'default_confidence': 15.0
            })
        }

    except Exception as e:
        logger.error(f"Error in final_results Lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

