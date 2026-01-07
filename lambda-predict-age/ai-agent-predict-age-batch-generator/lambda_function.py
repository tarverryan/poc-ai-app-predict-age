import json
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Generate batch IDs for parallel prediction processing.
    Creates an array of batch IDs from 0 to 897 (898 total batches).
    Each batch will process ~420K records (378M total / 898).
    """
    try:
        total_batches = 898  # 378,024,173 records / 420,962 ≈ 898 batches
        
        logger.info(f"Generating {total_batches} batch IDs for parallel prediction (~420K records each)")
        
        # Generate array of batch IDs
        batch_ids = list(range(total_batches))
        
        logger.info(f"Generated {len(batch_ids)} batch IDs (0 to {total_batches-1})")
        
        return {
            'statusCode': 200,
            'batch_ids': batch_ids,
            'total_batches': total_batches,
            'records_per_batch': 420962,  # ~420K records per batch
            'total_records': 378024173
        }

    except Exception as e:
        logger.error(f"Error generating batch IDs: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }

