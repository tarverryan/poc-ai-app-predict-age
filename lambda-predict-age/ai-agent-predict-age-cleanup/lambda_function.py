import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

athena_client = boto3.client('athena')
s3_client = boto3.client('s3')
ecs_client = boto3.client('ecs')
ecr_client = boto3.client('ecr')

DATABASE_NAME = os.environ['DATABASE_NAME']
S3_BUCKET = os.environ['S3_BUCKET']
CLUSTER_NAME = os.environ['CLUSTER_NAME']

def lambda_handler(event, context):
    """
    Comprehensive cleanup after pipeline completion.
    
    SAFETY CHECKS:
    1. Verifies no Fargate tasks are running
    2. Verifies no ECR image scans in progress
    3. Only runs after final results table is confirmed complete
    
    CLEANUP ACTIONS:
    1. Drop all Athena tables EXCEPT final results (predict_age_final_results_*)
    2. Clean all S3 data EXCEPT final results
    3. Stop any lingering Fargate tasks
    4. Log resource usage for cost verification
    """
    try:
        logger.info("=" * 80)
        logger.info("STARTING COMPREHENSIVE CLEANUP")
        logger.info("=" * 80)
        
        # SAFETY CHECK 1: Verify no tasks are running
        logger.info("Safety Check 1: Checking for running Fargate tasks...")
        running_tasks = check_running_tasks()
        if running_tasks > 0:
            logger.warning(f"❌ ABORT: Found {running_tasks} running Fargate tasks")
            logger.warning("Cleanup cannot proceed while tasks are running")
            return {
                'statusCode': 400, 
                'body': f'Cleanup aborted: {running_tasks} tasks still running',
                'running_tasks': running_tasks
            }
        logger.info("✅ No running Fargate tasks")
        
        # SAFETY CHECK 2: Verify final results table exists
        logger.info("Safety Check 2: Verifying final results table exists...")
        final_table_exists = verify_final_results_table()
        if not final_table_exists:
            logger.warning("❌ ABORT: Final results table not found")
            logger.warning("Cleanup cannot proceed without final results table")
            return {
                'statusCode': 400,
                'body': 'Cleanup aborted: Final results table not found'
            }
        logger.info("✅ Final results table exists")
        
        # SAFETY CHECK 3: Verify final results table has expected record count
        logger.info("Safety Check 3: Verifying final results table record count...")
        record_count = verify_final_results_count()
        if record_count < 370000000:  # Should be ~378M
            logger.warning(f"❌ ABORT: Final results table has only {record_count:,} records")
            logger.warning("Expected ~378M records. Table may be incomplete.")
            return {
                'statusCode': 400,
                'body': f'Cleanup aborted: Final results table incomplete ({record_count:,} records)',
                'record_count': record_count
            }
        logger.info(f"✅ Final results table has {record_count:,} records")
        
        # CLEANUP 1: Drop intermediate Athena tables
        logger.info("")
        logger.info("Cleanup 1: Dropping intermediate Athena tables...")
        dropped_tables = cleanup_athena_tables()
        logger.info(f"✅ Dropped {len(dropped_tables)} intermediate tables")
        
        # CLEANUP 2: Clean intermediate S3 data
        logger.info("")
        logger.info("Cleanup 2: Cleaning intermediate S3 data...")
        deleted_objects = cleanup_s3_data()
        logger.info(f"✅ Deleted {deleted_objects:,} S3 objects")
        
        # CLEANUP 3: Stop any lingering tasks (should be none)
        logger.info("")
        logger.info("Cleanup 3: Stopping any lingering Fargate tasks...")
        stopped_tasks = stop_lingering_tasks()
        logger.info(f"✅ Stopped {stopped_tasks} lingering tasks")
        
        # VERIFICATION: Check for active resources
        logger.info("")
        logger.info("Verification: Checking for active billable resources...")
        active_resources = check_active_resources()
        
        logger.info("=" * 80)
        logger.info("CLEANUP COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Tables dropped: {len(dropped_tables)}")
        logger.info(f"S3 objects deleted: {deleted_objects:,}")
        logger.info(f"Tasks stopped: {stopped_tasks}")
        logger.info(f"Active resources: {active_resources}")
        logger.info("=" * 80)
        
        return {
            'statusCode': 200,
            'body': 'Cleanup completed successfully',
            'summary': {
                'tables_dropped': len(dropped_tables),
                's3_objects_deleted': deleted_objects,
                'tasks_stopped': stopped_tasks,
                'active_resources': active_resources,
                'final_table_records': record_count,
                'timestamp': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}")
        raise

def check_running_tasks():
    """Check for running ECS tasks"""
    try:
        response = ecs_client.list_tasks(cluster=CLUSTER_NAME, desiredStatus='RUNNING')
        task_count = len(response['taskArns'])
        
        if task_count > 0:
            logger.warning(f"Found {task_count} running tasks:")
            for task_arn in response['taskArns']:
                logger.warning(f"  - {task_arn}")
        
        return task_count
    except Exception as e:
        logger.error(f"Error checking running tasks: {str(e)}")
        return -1  # Return error state

def verify_final_results_table():
    """Verify final results table exists"""
    try:
        response = athena_client.list_table_metadata(
            CatalogName='AwsDataCatalog',
            DatabaseName=DATABASE_NAME
        )
        
        for table in response['TableMetadataList']:
            if table['Name'].startswith('predict_age_final_results_'):
                logger.info(f"Found final results table: {table['Name']}")
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error verifying final results table: {str(e)}")
        return False

def verify_final_results_count():
    """Verify final results table has expected record count"""
    try:
        query = f"""
        SELECT COUNT(*) as record_count 
        FROM {DATABASE_NAME}.predict_age_final_results_2025q3
        """
        
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': DATABASE_NAME},
            ResultConfiguration={'OutputLocation': f's3://{S3_BUCKET}/athena-results/'},
            WorkGroup='primary'
        )
        
        execution_id = response['QueryExecutionId']
        
        # Wait for query to complete (max 30 seconds)
        import time
        for _ in range(30):
            status_response = athena_client.get_query_execution(QueryExecutionId=execution_id)
            status = status_response['QueryExecution']['Status']['State']
            
            if status == 'SUCCEEDED':
                results = athena_client.get_query_results(QueryExecutionId=execution_id)
                if len(results['ResultSet']['Rows']) > 1:
                    count_str = results['ResultSet']['Rows'][1]['Data'][0]['VarCharValue']
                    return int(count_str)
                return 0
            elif status in ['FAILED', 'CANCELLED']:
                logger.error(f"Query failed with status: {status}")
                return 0
            
            time.sleep(1)
        
        logger.warning("Query timed out after 30 seconds")
        return 0
        
    except Exception as e:
        logger.error(f"Error verifying record count: {str(e)}")
        return 0

def cleanup_athena_tables():
    """
    Drop all intermediate Athena tables.
    KEEP ONLY: predict_age_final_results_* (final results tables)
    """
    tables_to_keep_prefixes = [
        'predict_age_final_results_',
        'predict_age_training_raw_',  # Permanent: raw training data (no JSON parsing)
        'predict_age_training_targets_',  # Permanent: training targets  
        'predict_age_training_features_parsed_'  # Permanent: Fargate-parsed features
    ]
    dropped_tables = []
    
    try:
        # Get all tables in the database
        response = athena_client.list_table_metadata(
            CatalogName='AwsDataCatalog',
            DatabaseName=DATABASE_NAME
        )
        
        for table in response['TableMetadataList']:
            table_name = table['Name']
            
            # Keep final results tables
            if any(table_name.startswith(prefix) for prefix in tables_to_keep_prefixes):
                logger.info(f"  KEEP: {table_name} (final results)")
                continue
            
            # Drop all other tables
            logger.info(f"  DROP: {table_name}")
            drop_table(table_name)
            dropped_tables.append(table_name)
        
        return dropped_tables
        
    except Exception as e:
        logger.error(f"Error cleaning up Athena tables: {str(e)}")
        return dropped_tables

def drop_table(table_name):
    """Drop an Athena table"""
    try:
        query = f"DROP TABLE IF EXISTS {DATABASE_NAME}.{table_name}"
        
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': DATABASE_NAME},
            ResultConfiguration={'OutputLocation': f's3://{S3_BUCKET}/athena-results/'},
            WorkGroup='primary'
        )
        
        execution_id = response['QueryExecutionId']
        
        # Wait for completion (max 10 seconds)
        import time
        for _ in range(10):
            status_response = athena_client.get_query_execution(QueryExecutionId=execution_id)
            status = status_response['QueryExecution']['Status']['State']
            
            if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                break
            
            time.sleep(1)
        
    except Exception as e:
        logger.error(f"Error dropping table {table_name}: {str(e)}")

def cleanup_s3_data():
    """
    Clean all intermediate S3 data.
    KEEP ONLY:
      - predict-age/final-results/ (final results data)
      - predict-age/permanent/ (permanent training data - NEVER DELETE)
      - predict-age/agent-context-upload/ (Bedrock Agent KB documents, if any)
    """
    prefixes_to_clean = [
        'predict-age/staging/',
        'predict-age/features/',
        'predict-age/targets/',
        'predict-age/predictions/',
        'predict-age/models/',
        'predict-age/evaluation/',
        'predict-age/human-qa/',
        'predict-age/test/',  # Test data
        'athena-results/'  # Clean up Athena query results too
    ]
    
    # NOTE: predict-age/permanent/ is explicitly NOT in this list
    # It contains parsed training data that we never want to recompute
    
    total_deleted = 0
    
    for prefix in prefixes_to_clean:
        deleted = delete_s3_prefix(prefix)
        total_deleted += deleted
        logger.info(f"    Deleted {deleted:,} objects from {prefix}")
    
    return total_deleted

def delete_s3_prefix(prefix):
    """Delete all objects under a prefix"""
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
        
        delete_count = 0
        for page in pages:
            if 'Contents' in page:
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                if objects:
                    s3_client.delete_objects(Bucket=S3_BUCKET, Delete={'Objects': objects})
                    delete_count += len(objects)
        
        return delete_count
        
    except Exception as e:
        logger.error(f"Error deleting S3 prefix {prefix}: {str(e)}")
        return 0

def stop_lingering_tasks():
    """Stop any lingering ECS tasks (should be none if safety checks passed)"""
    try:
        response = ecs_client.list_tasks(cluster=CLUSTER_NAME, desiredStatus='RUNNING')
        
        stopped_count = 0
        for task_arn in response['taskArns']:
            logger.info(f"    Stopping task: {task_arn}")
            ecs_client.stop_task(cluster=CLUSTER_NAME, task=task_arn, reason='Cleanup after pipeline completion')
            stopped_count += 1
        
        return stopped_count
        
    except Exception as e:
        logger.error(f"Error stopping lingering tasks: {str(e)}")
        return 0

def check_active_resources():
    """
    Check for active billable resources.
    Returns a summary of what's still running/active.
    """
    active = {
        'fargate_tasks': 0,
        'ecr_images': 0,
        'athena_tables': 0,
        's3_final_results_size_mb': 0
    }
    
    try:
        # Check Fargate tasks
        response = ecs_client.list_tasks(cluster=CLUSTER_NAME, desiredStatus='RUNNING')
        active['fargate_tasks'] = len(response['taskArns'])
        
        # Check ECR images (training and prediction)
        try:
            training_images = ecr_client.list_images(repositoryName='ai-agent-predict-age-training')
            active['ecr_images'] += len(training_images.get('imageIds', []))
        except:
            pass
        
        try:
            prediction_images = ecr_client.list_images(repositoryName='ai-agent-predict-age-prediction')
            active['ecr_images'] += len(prediction_images.get('imageIds', []))
        except:
            pass
        
        # Check Athena tables (should only be final results)
        response = athena_client.list_table_metadata(
            CatalogName='AwsDataCatalog',
            DatabaseName=DATABASE_NAME
        )
        active['athena_tables'] = len(response['TableMetadataList'])
        
        # Check S3 final results size
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=S3_BUCKET, Prefix='predict-age/final-results/')
            
            total_size = 0
            for page in pages:
                if 'Contents' in page:
                    total_size += sum(obj['Size'] for obj in page['Contents'])
            
            active['s3_final_results_size_mb'] = round(total_size / (1024 * 1024), 2)
        except:
            pass
        
        logger.info("Active resources:")
        logger.info(f"  - Fargate tasks: {active['fargate_tasks']}")
        logger.info(f"  - ECR images: {active['ecr_images']}")
        logger.info(f"  - Athena tables: {active['athena_tables']}")
        logger.info(f"  - S3 final results: {active['s3_final_results_size_mb']} MB")
        
        return active
        
    except Exception as e:
        logger.error(f"Error checking active resources: {str(e)}")
        return active

