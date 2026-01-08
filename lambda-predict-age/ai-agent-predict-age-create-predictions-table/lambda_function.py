import json
import boto3
import time
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
athena_client = boto3.client('athena')

import os

DATABASE_NAME = os.environ.get('DATABASE_NAME', 'ml_predict_age')
PREDICTIONS_TABLE_NAME = f'predict_age_predictions_{os.environ.get("YYYYQQ", "YYYYQQ")}'
S3_BUCKET = os.environ.get('S3_BUCKET')
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
                return True
            elif status == 'FAILED':
                error_reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                logger.error(f"Query {execution_id} failed: {error_reason}")
                return False
            elif status == 'CANCELLED':
                logger.error(f"Query {execution_id} was cancelled")
                return False
            
            logger.info(f"Query {execution_id} status: {status}. Waiting...")
            time.sleep(2)
            
    except Exception as e:
        logger.error(f"Error waiting for query completion: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Pre-create predictions table to avoid race conditions in parallel execution.
    This Lambda is called ONCE before parallel prediction tasks start.
    """
    try:
        logger.info(f"Creating predictions table {PREDICTIONS_TABLE_NAME}")
        
        # Drop existing table first to ensure clean schema
        drop_query = f"DROP TABLE IF EXISTS {DATABASE_NAME}.{PREDICTIONS_TABLE_NAME}"
        drop_execution_id = execute_athena_query(drop_query, "Dropping existing predictions table")
        wait_for_query_completion(drop_execution_id)
        logger.info(f"Existing table dropped (if it existed)")
        
        # Create table with Parquet format (updated from JSONL)
        # Schema matches actual Parquet files: id (bigint), predicted_age (int), confidence_score (double), etc.
        create_query = f"""
        CREATE EXTERNAL TABLE {DATABASE_NAME}.{PREDICTIONS_TABLE_NAME} (
            id bigint,
            predicted_age int,
            confidence_score double,
            prediction_ts string,
            model_version string
        )
        STORED AS PARQUET
        LOCATION 's3://{S3_BUCKET}/predict-age/predictions/'
        """
        
        execution_id = execute_athena_query(create_query, f"Creating predictions table")
        success = wait_for_query_completion(execution_id)
        
        if success:
            logger.info(f"✅ Predictions table {PREDICTIONS_TABLE_NAME} is ready")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Predictions table {PREDICTIONS_TABLE_NAME} created successfully',
                    'execution_id': execution_id,
                    'timestamp': datetime.now().isoformat()
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to create predictions table',
                    'execution_id': execution_id,
                    'timestamp': datetime.now().isoformat()
                })
            }

    except Exception as e:
        logger.error(f"Error in CreatePredictionsTable Lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

