import json
import boto3
import time
import os
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
athena_client = boto3.client('athena')
s3_client = boto3.client('s3')

# Configuration from environment variables
S3_BUCKET = os.environ.get('S3_BUCKET')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'ml_predict_age')

if not S3_BUCKET:
    raise ValueError("S3_BUCKET environment variable is required")

def strip_sql_comments(sql):
    """Remove SQL comments from query string"""
    lines = sql.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove single-line comments (-- style)
        if '--' in line:
            line = line[:line.index('--')]
        # Keep line if it has content after stripping
        stripped = line.strip()
        if stripped:
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def read_sql_file(filename):
    """Read SQL file content and strip comments"""
    try:
        with open(filename, 'r') as f:
            sql = f.read()
            # Strip comments before returning
            return strip_sql_comments(sql)
    except Exception as e:
        logger.error(f"Error reading SQL file {filename}: {str(e)}")
        raise

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
    Lambda function to orchestrate feature engineering for training or full evaluation.
    """
    try:
        logger.info(f"Received event: {event}")

        mode = event.get('mode', 'training')

        if mode == 'full_evaluation':
            # Full evaluation mode: Create evaluation features for all 378M PIDs
            logger.info("Processing full evaluation features for all 378M PIDs")
            
            # Read full evaluation features query from SQL file
            features_query = read_sql_file('full_evaluation_features_378m.sql')
            
            # Execute features query
            execution_id = execute_athena_query(features_query, "Creating full evaluation features table")
            wait_for_query_completion(execution_id)
            
            logger.info("Full evaluation feature engineering completed successfully")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Full evaluation feature engineering completed successfully',
                    'execution_id': execution_id,
                    'timestamp': datetime.now().isoformat()
                })
            }
        else:
            # Training mode: Create training features and targets
            logger.info("Processing training features")
            
            # Read training features query from SQL file
            features_query = read_sql_file('real_training_features_14m.sql')
            
            # Execute features query
            features_execution_id = execute_athena_query(features_query, "Creating training features table")
            wait_for_query_completion(features_execution_id)
            
            # Create targets table
            targets_query = read_sql_file('real_training_targets_14m.sql')
            targets_execution_id = execute_athena_query(targets_query, "Creating targets table")
            wait_for_query_completion(targets_execution_id)
            
            logger.info("Training feature engineering completed successfully")
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Training feature engineering completed successfully',
                    'features_execution_id': features_execution_id,
                    'targets_execution_id': targets_execution_id,
                    'timestamp': datetime.now().isoformat()
                })
            }

    except Exception as e:
        logger.error(f"Error in feature engineering Lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

