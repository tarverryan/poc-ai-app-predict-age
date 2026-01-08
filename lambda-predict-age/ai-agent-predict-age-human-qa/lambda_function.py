import json
import boto3
import time
import logging
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
athena_client = boto3.client('athena')
s3_client = boto3.client('s3')

# Configuration from environment variables
S3_BUCKET = os.environ.get('S3_BUCKET')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'ml_predict_age')
YYYYQQ = os.environ.get('YYYYQQ', 'YYYYQQ')

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
    Lambda function to create Human QA table with 1:1 mapping to source table.
    Ensures every ID from the source table has an age prediction.
    """
    try:
        # Allow source table to be configurable for testing
        source_table = event.get('source_table', 'predict_age_full_evaluation_raw_378m')
        logger.info(f"Starting Human QA table creation with 1:1 mapping from {source_table}")
        
        # First, drop the table if it exists (including S3 data)
        drop_query = f"DROP TABLE IF EXISTS {DATABASE_NAME}.predict_age_human_qa_{YYYYQQ}"
        drop_execution_id = execute_athena_query(drop_query, "Dropping existing Human QA table")
        wait_for_query_completion(drop_execution_id)
        logger.info("Existing table dropped successfully")
        
        # Clean up S3 directory
        bucket = S3_BUCKET
        prefix = f'predict-age/human-qa/predict_age_human_qa_{YYYYQQ}/'
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            delete_keys = []
            for page in pages:
                if 'Contents' in page:
                    delete_keys.extend([{'Key': obj['Key']} for obj in page['Contents']])
            if delete_keys:
                s3_client.delete_objects(Bucket=bucket, Delete={'Objects': delete_keys})
                logger.info(f"Cleaned up {len(delete_keys)} S3 objects")
        except Exception as e:
            logger.warning(f"Error cleaning S3: {str(e)}")
        
        # Create Human QA table with LEFT JOIN to ensure all source IDs are included
        # OPTIMIZED: No DISTINCT (id is unique), No ORDER BY (not needed)
        query = f"""
        CREATE TABLE {DATABASE_NAME}.predict_age_human_qa_{YYYYQQ}
        WITH (
            external_location = 's3://{S3_BUCKET}/predict-age/human-qa/predict_age_human_qa_{YYYYQQ}/',
            format = 'PARQUET',
            parquet_compression = 'SNAPPY'
        ) AS
        SELECT 
            s.id,
            COALESCE(p.predicted_age, 35) as predicted_age,
            COALESCE(p.confidence_score, 15.0) as confidence_score,
            CAST(current_timestamp AS VARCHAR) as qa_timestamp,
            COALESCE(p.model_version, 'v1.0_xgboost') as model_version,
            CASE 
                WHEN p.id IS NULL THEN 'MISSING_PREDICTION'
                ELSE 'HAS_PREDICTION'
            END as prediction_status
        FROM (
            -- Source table: Configurable (default: full_evaluation_features_378m)
            -- This ensures 1:1 mapping with all predictions
            SELECT CAST(id AS BIGINT) as id
            FROM "{DATABASE_NAME}"."{source_table}"
            WHERE id IS NOT NULL
        ) s
        LEFT JOIN {DATABASE_NAME}.predict_age_predictions_{YYYYQQ} p
        ON s.id = p.id
        """
        
        execution_id = execute_athena_query(query, "Creating Human QA table with 1:1 mapping")
        wait_for_query_completion(execution_id)
        
        logger.info("Human QA table created successfully with 1:1 mapping!")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Human QA table created successfully with 1:1 mapping!',
                'table_name': f'predict_age_human_qa_{YYYYQQ}',
                'execution_id': execution_id,
                'timestamp': datetime.now().isoformat()
            })
        }

    except Exception as e:
        logger.error(f"Error in Human QA Lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

