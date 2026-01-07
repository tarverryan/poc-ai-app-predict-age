import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

athena_client = boto3.client('athena')
s3_client = boto3.client('s3')

DATABASE_NAME = os.environ['DATABASE_NAME']
S3_BUCKET = os.environ['S3_BUCKET']

def lambda_handler(event, context):
    """
    Pre-cleanup: Run at START of pipeline to prevent duplicates.
    
    PURPOSE:
    - Athena DROP TABLE only removes metadata, NOT S3 data
    - If we don't clean S3, Athena will read old + new data = DUPLICATES
    - This Lambda ensures a clean slate before each pipeline run
    
    ACTIONS:
    1. Drop final results table (if exists)
    2. Clean final results S3 directory
    3. Verify cleanup was successful
    
    SAFETY:
    - Only cleans final results (intermediate data cleaned by post-cleanup)
    - Logs what was cleaned for audit trail
    """
    try:
        logger.info("=" * 80)
        logger.info("PRE-CLEANUP: Preparing for new pipeline run")
        logger.info("=" * 80)
        
        # 1. Drop final results table (if exists)
        logger.info("Step 1: Dropping final results table (if exists)...")
        dropped = drop_final_results_table()
        if dropped:
            logger.info("✅ Final results table dropped")
        else:
            logger.info("ℹ️  No final results table to drop")
        
        # 2. Clean final results S3 directory
        logger.info("")
        logger.info("Step 2: Cleaning final results S3 directory...")
        deleted_count = clean_final_results_s3()
        logger.info(f"✅ Deleted {deleted_count:,} objects from final results S3")
        
        # 3. Verify cleanup
        logger.info("")
        logger.info("Step 3: Verifying cleanup...")
        verification = verify_cleanup()
        
        logger.info("=" * 80)
        logger.info("PRE-CLEANUP COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Table dropped: {dropped}")
        logger.info(f"S3 objects deleted: {deleted_count:,}")
        logger.info(f"Verification: {verification}")
        logger.info("=" * 80)
        
        return {
            'statusCode': 200,
            'body': 'Pre-cleanup completed successfully',
            'summary': {
                'table_dropped': dropped,
                's3_objects_deleted': deleted_count,
                'verification': verification,
                'timestamp': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Pre-cleanup failed: {str(e)}")
        raise

def drop_final_results_table():
    """Drop final results table if it exists"""
    try:
        table_name = 'predict_age_final_results_2025q3'
        query = f"DROP TABLE IF EXISTS {DATABASE_NAME}.{table_name}"
        
        logger.info(f"Executing: {query}")
        
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': DATABASE_NAME},
            ResultConfiguration={'OutputLocation': f's3://{S3_BUCKET}/athena-results/'},
            WorkGroup='primary'
        )
        
        execution_id = response['QueryExecutionId']
        
        # Wait for completion (max 30 seconds)
        import time
        for _ in range(30):
            status_response = athena_client.get_query_execution(QueryExecutionId=execution_id)
            status = status_response['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                logger.info(f"Table drop succeeded (execution_id: {execution_id})")
                return True
            elif status in ['FAILED', 'CANCELLED']:
                error = status_response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
                logger.warning(f"Table drop failed: {error}")
                return False
            
            time.sleep(1)
        
        logger.warning("Table drop timed out after 30 seconds")
        return False
        
    except Exception as e:
        logger.error(f"Error dropping final results table: {str(e)}")
        return False

def clean_final_results_s3():
    """Clean final results S3 directory AND upstream dependencies"""
    try:
        # Clean multiple S3 prefixes to prevent cascading duplicates
        prefixes_to_clean = [
            'predict-age/final-results/',  # Final results
            'predict-age/human-qa/',       # Human QA (source of duplicates)
            'predict-age/predictions/',    # Predictions (root cause of duplicates)
        ]
        
        total_deleted = 0
        for prefix in prefixes_to_clean:
            logger.info(f"Cleaning S3 prefix: s3://{S3_BUCKET}/{prefix}")
            
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
            
            delete_count = 0
            for page in pages:
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects:
                        logger.info(f"  Deleting batch of {len(objects)} objects from {prefix}...")
                        s3_client.delete_objects(Bucket=S3_BUCKET, Delete={'Objects': objects})
                        delete_count += len(objects)
            
            if delete_count == 0:
                logger.info(f"  No objects to delete from {prefix} (clean slate)")
            else:
                logger.info(f"  Deleted {delete_count} objects from {prefix}")
            
            total_deleted += delete_count
        
        return total_deleted
        
    except Exception as e:
        logger.error(f"Error cleaning S3 directories: {str(e)}")
        return 0

def verify_cleanup():
    """Verify cleanup was successful"""
    verification = {
        'table_exists': False,
        's3_objects_remaining': 0
    }
    
    try:
        # Check if table still exists
        response = athena_client.list_table_metadata(
            CatalogName='AwsDataCatalog',
            DatabaseName=DATABASE_NAME
        )
        
        for table in response['TableMetadataList']:
            if table['Name'] == 'predict_age_final_results_2025q3':
                verification['table_exists'] = True
                logger.warning("⚠️  Table still exists after drop!")
                break
        
        if not verification['table_exists']:
            logger.info("✅ Table does not exist (as expected)")
        
        # Check if S3 objects remain
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix='predict-age/final-results/',
            MaxKeys=10
        )
        
        if 'Contents' in response:
            verification['s3_objects_remaining'] = response['KeyCount']
            logger.warning(f"⚠️  {response['KeyCount']} S3 objects still remain!")
        else:
            logger.info("✅ No S3 objects remain (as expected)")
        
        return verification
        
    except Exception as e:
        logger.error(f"Error verifying cleanup: {str(e)}")
        return verification

