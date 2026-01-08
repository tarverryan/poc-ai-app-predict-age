#!/usr/bin/env python3
"""
Fargate Prediction with Inline JSON Parsing
Reads raw data, parses JSON on-the-fly, makes predictions
Optimized for cost: no pre-parsing required!
"""

import os
import time
import json
import boto3
import logging
from datetime import datetime
import joblib
import pandas as pd
import numpy as np
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS clients
s3_client = boto3.client('s3')
athena_client = boto3.client('athena')

# Environment variables
S3_BUCKET = os.environ.get('S3_BUCKET')
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'ml_predict_age')
WORKGROUP = os.environ.get('WORKGROUP', 'ai-agent-predict-age')

if not S3_BUCKET:
    raise ValueError("S3_BUCKET environment variable is required")
BATCH_ID = int(os.environ.get('BATCH_ID', '0'))
RAW_TABLE = os.environ.get('RAW_TABLE', 'predict_age_training_raw_14m')  # For testing
TOTAL_BATCHES = int(os.environ.get('TOTAL_BATCHES', '898'))

# JSON parsing functions (from feature parser)
def parse_education_level(edu_str):
    """Parse education level from JSON string"""
    if pd.isna(edu_str) or edu_str == '' or edu_str == '[]':
        return 2
    try:
        edu_lower = str(edu_str).lower()
        if 'phd' in edu_lower or 'doctorate' in edu_lower:
            return 5
        elif 'master' in edu_lower or 'mba' in edu_lower:
            return 4
        elif 'bachelor' in edu_lower:
            return 3
        elif 'associate' in edu_lower:
            return 2
        elif 'high school' in edu_lower:
            return 1
        else:
            return 2
    except:
        return 2

def parse_graduation_year(edu_str):
    """Parse graduation year from education JSON"""
    if pd.isna(edu_str) or edu_str == '' or edu_str == '[]':
        return None
    try:
        edu_obj = json.loads(edu_str)
        if isinstance(edu_obj, list) and len(edu_obj) > 0:
            end_date = edu_obj[0].get('end_date')
            if end_date:
                return int(end_date)
    except:
        pass
    return None

def parse_json_array_length(json_str):
    """Parse JSON array and return length"""
    if pd.isna(json_str) or json_str == '' or json_str == '[]':
        return 0
    try:
        obj = json.loads(json_str)
        if isinstance(obj, list):
            return len(obj)
    except:
        pass
    return 0

def calc_total_career_years(work_exp_str):
    """Calculate total career years from work experience JSON"""
    if pd.isna(work_exp_str) or work_exp_str == '' or work_exp_str == '[]':
        return None
    try:
        work_exp = json.loads(work_exp_str)
        if isinstance(work_exp, list) and len(work_exp) > 0:
            years = []
            for job in work_exp:
                start = job.get('start_year')
                end = job.get('end_year', datetime.now().year)
                if start:
                    years.append(end - start)
            if years:
                return sum(years)
    except:
        pass
    return None

def create_features_from_raw(df_raw):
    """Create ML features from raw data with JSON parsing"""
    logger.info(f"Parsing JSON and creating features for {len(df_raw)} rows...")
    start_time = time.time()
    
    df = df_raw.copy()
    
    # Parse JSON fields
    logger.info("Parsing education...")
    df['education_level_encoded'] = df['education'].apply(parse_education_level)
    df['graduation_year'] = df['education'].apply(parse_graduation_year)
    
    logger.info("Parsing work experience and skills...")
    df['number_of_jobs'] = df['work_experience'].apply(parse_json_array_length).astype(float)
    df['skill_count'] = df['skills'].apply(parse_json_array_length).astype(float)
    df['total_career_years'] = df['work_experience'].apply(calc_total_career_years).astype(float)
    
    # Fill missing values
    df['total_career_years'] = df['total_career_years'].fillna(df['number_of_jobs'] * 3)
    df['graduation_year'] = df['graduation_year'].fillna(2010)
    
    # Job churn rate
    df['job_churn_rate'] = np.where(df['total_career_years'] > 0,
                                     df['number_of_jobs'] / df['total_career_years'],
                                     0.3)
    
    # Job level encoding
    def encode_job_level(level):
        if pd.isna(level) or level == '':
            return 2
        elif level == 'C-Team':
            return 4
        elif level == 'Manager':
            return 3
        else:
            return 2
    
    df['job_level_encoded'] = df['job_level'].apply(encode_job_level)
    
    # Job seniority score
    job_level_map = {'C-Team': 4, 'Manager': 3, 'Staff': 2}
    def calc_seniority(row):
        level_score = job_level_map.get(row['job_level'], 2)
        title = str(row['job_title']).lower() if pd.notna(row['job_title']) else ''
        if 'chief' in title or 'ceo' in title or 'president' in title:
            return 5
        elif 'vp' in title or 'vice president' in title:
            return 4
        elif 'manager' in title or 'director' in title:
            return 3
        else:
            return level_score
    
    df['job_seniority_score'] = df.apply(calc_seniority, axis=1)
    
    # Compensation encoding
    comp_map = {
        '$0-25k': 1, '$25-50k': 2, '$50-75k': 3, '$75-100k': 4,
        '$100-150k': 5, '$150-250k': 6, '$250k+': 7
    }
    df['compensation_encoded'] = df['compensation_range'].map(comp_map).fillna(4).astype(int)
    
    # Company size encoding
    size_map = {
        '1-10': 1, '11-50': 2, '51-200': 3, '201-500': 4,
        '501-1000': 5, '1001-5000': 6, '5001-10000': 7, '10000+': 8
    }
    df['company_size_encoded'] = df['employee_range'].map(size_map).fillna(5).astype(int)
    
    # LinkedIn activity score (convert to numeric first)
    df['linkedin_connection_count'] = pd.to_numeric(df['linkedin_connection_count'], errors='coerce').fillna(0).astype(int)
    df['linkedin_activity_score'] = np.where(
        df['linkedin_connection_count'] >= 500, 1.0,
        np.where(df['linkedin_connection_count'] >= 100, 0.7,
                 np.where(df['linkedin_connection_count'] > 0, 0.3, 0.0))
    )
    
    # Days since profile update
    def calc_days_since_update(ev_date):
        if pd.isna(ev_date) or ev_date == '':
            return 365
        try:
            ev_datetime = pd.to_datetime(ev_date)
            return int((datetime.now() - ev_datetime).days)
        except:
            return 365
    
    df['days_since_profile_update'] = df['ev_last_date'].apply(calc_days_since_update)
    
    # Social media presence score
    def calc_social_score(row):
        linkedin_valid = row['linkedin_url_is_valid'] == 'true'
        has_facebook = pd.notna(row['facebook_url']) and row['facebook_url'] != ''
        has_twitter = pd.notna(row['twitter_url']) and row['twitter_url'] != ''
        
        if linkedin_valid and has_facebook and has_twitter:
            return 1.0
        elif linkedin_valid and (has_facebook or has_twitter):
            return 0.7
        elif linkedin_valid:
            return 0.5
        else:
            return 0.2
    
    df['social_media_presence_score'] = df.apply(calc_social_score, axis=1)
    
    # Email engagement score
    def calc_email_score(row):
        has_work = pd.notna(row['work_email']) and row['work_email'] != ''
        has_personal = pd.notna(row['personal_email']) and row['personal_email'] != ''
        
        if has_work and has_personal:
            return 1.0
        elif has_work or has_personal:
            return 0.5
        else:
            return 0.0
    
    df['email_engagement_score'] = df.apply(calc_email_score, axis=1)
    
    # Industry typical age
    industry_age_map = {
        'Technology': 35, 'Consulting': 38, 'Finance': 42, 'Healthcare': 40,
        'Education': 45, 'Retail': 32, 'Manufacturing': 43, 'Real Estate': 44
    }
    df['industry_typical_age'] = df['industry'].astype(str).map(industry_age_map).fillna(40).astype(int)
    
    # Job function encoding
    function_map = {
        'Engineering': 0, 'Sales': 1, 'Marketing': 2, 'Operations': 3,
        'Finance': 4, 'HR': 5, 'Product': 6, 'Other': 7
    }
    df['job_function_encoded'] = df['job_function'].map(function_map).fillna(7).astype(int)
    
    # Company revenue encoding
    revenue_map = {
        '$0-1M': 1, '$1-10M': 2, '$10-50M': 3, '$50-100M': 4,
        '$100-500M': 5, '$500M-1B': 6, '$1B+': 7
    }
    df['company_revenue_encoded'] = df['revenue_range'].map(revenue_map).fillna(5).astype(int)
    
    # Tenure months (from job_start_date)
    def calc_tenure(start_date):
        if pd.isna(start_date) or start_date == '':
            return 36
        try:
            start = pd.to_datetime(start_date)
            months = int((datetime.now() - start).days / 30)
            return max(0, min(months, 600))
        except:
            return 36
    
    df['tenure_months'] = df['job_start_date'].apply(calc_tenure)
    
    # Quarter (current quarter)
    df['quarter'] = (datetime.now().month - 1) // 3 + 1
    
    # Interaction features
    df['tenure_job_level_interaction'] = df['tenure_months'] * df['job_level_encoded']
    df['comp_size_interaction'] = df['compensation_encoded'] * df['company_size_encoded']
    
    # Select final feature columns (21 features)
    feature_cols = [
        'tenure_months', 'job_level_encoded', 'job_seniority_score',
        'compensation_encoded', 'company_size_encoded', 'linkedin_activity_score',
        'days_since_profile_update', 'social_media_presence_score', 
        'email_engagement_score', 'industry_typical_age', 'job_function_encoded',
        'company_revenue_encoded', 'quarter', 'education_level_encoded',
        'graduation_year', 'number_of_jobs', 'skill_count', 'total_career_years',
        'job_churn_rate', 'tenure_job_level_interaction', 'comp_size_interaction'
    ]
    
    elapsed = time.time() - start_time
    logger.info(f"✅ Feature creation completed in {elapsed:.2f}s ({len(df)/elapsed:.0f} rows/sec)")
    
    return df[['id'] + feature_cols]

def load_models_from_s3():
    """Load trained models from S3"""
    logger.info("Loading models from S3...")
    
    # Load XGBoost model
    xgb_key = 'predict-age/models/xgboost_model.joblib'
    xgb_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=xgb_key)
    model_xgb = joblib.load(BytesIO(xgb_obj['Body'].read()))
    logger.info("XGBoost model loaded")
    
    # Load Quantile model
    qrf_key = 'predict-age/models/qrf_model.joblib'
    qrf_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=qrf_key)
    model_quantile = joblib.load(BytesIO(qrf_obj['Body'].read()))
    logger.info("Quantile model loaded")
    
    return model_xgb, model_quantile

def load_raw_data_for_batch():
    """Load raw data from Athena for this batch (ONLY PIDs missing age data)"""
    logger.info(f"Loading raw data for batch {BATCH_ID}/{TOTAL_BATCHES}...")
    
    # Query raw data with modulo batching - ONLY predict for PIDs with missing age data
    query = f"""
    SELECT *
    FROM {DATABASE_NAME}.{RAW_TABLE}
    WHERE id IS NOT NULL
    AND (birth_year IS NULL AND approximate_age IS NULL)
    AND MOD(CAST(id AS BIGINT), {TOTAL_BATCHES}) = {BATCH_ID}
    """
    
    # Execute query
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': DATABASE_NAME},
        WorkGroup=WORKGROUP,
        ResultConfiguration={'OutputLocation': f's3://{S3_BUCKET}/athena-results/'}
    )
    query_id = response['QueryExecutionId']
    logger.info(f"Athena query started: {query_id}")
    
    # Wait for completion
    while True:
        status_response = athena_client.get_query_execution(QueryExecutionId=query_id)
        status = status_response['QueryExecution']['Status']['State']
        
        if status == 'SUCCEEDED':
            break
        elif status in ['FAILED', 'CANCELLED']:
            reason = status_response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
            raise Exception(f"Query {status}: {reason}")
        
        time.sleep(2)
    
    logger.info(f"Query completed: {query_id}")
    
    # Read results from S3 (Athena writes to CSV)
    results_key = f'athena-results/{query_id}.csv'
    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=results_key)
    df = pd.read_csv(BytesIO(obj['Body'].read()))
    
    logger.info(f"Loaded {len(df)} raw records")
    return df

def save_predictions_to_s3(predictions_df):
    """Save predictions to S3 as Parquet"""
    output_key = f'predict-age/predictions/batch_{BATCH_ID:04d}.parquet'
    
    # Save to temp file
    tmp_file = f'/tmp/predictions_batch_{BATCH_ID}.parquet'
    predictions_df.to_parquet(tmp_file, index=False, compression='snappy')
    
    # Upload to S3
    s3_client.upload_file(tmp_file, S3_BUCKET, output_key)
    logger.info(f"✅ Predictions saved to s3://{S3_BUCKET}/{output_key}")
    
    return output_key

def main():
    """Main prediction function"""
    start_time = time.time()
    
    try:
        logger.info(f"=== Starting Prediction Batch {BATCH_ID} ===")
        logger.info(f"Total batches: {TOTAL_BATCHES}")
        
        # 1. Load models
        model_xgb, model_quantile = load_models_from_s3()
        
        # 2. Load raw data
        df_raw = load_raw_data_for_batch()
        
        if len(df_raw) == 0:
            logger.warning(f"No data for batch {BATCH_ID}")
            return {'statusCode': 200, 'predictions': 0}
        
        # 3. Parse JSON and create features
        df_features = create_features_from_raw(df_raw)
        
        # 4. Make predictions
        logger.info("Making predictions...")
        X = df_features.drop('id', axis=1).values
        
        predictions = model_xgb.predict(X)
        pred_lower = model_quantile['lower'].predict(X)
        pred_upper = model_quantile['upper'].predict(X)
        confidence_scores = pred_upper - pred_lower
        
        # 5. Prepare results
        df_results = pd.DataFrame({
            'id': df_features['id'],
            'predicted_age': np.clip(np.round(predictions), 18, 75).astype(int),
            'confidence_score': np.round(confidence_scores, 2),
            'prediction_ts': datetime.now().isoformat(),
            'model_version': 'v1.0_xgboost',
            'batch_id': BATCH_ID
        })
        
        # 6. Save to S3
        output_key = save_predictions_to_s3(df_results)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Batch {BATCH_ID} completed in {elapsed:.2f}s")
        logger.info(f"   Processed {len(df_results)} predictions")
        logger.info(f"   Average age: {df_results['predicted_age'].mean():.1f} years")
        logger.info(f"   Throughput: {len(df_results)/elapsed:.0f} rows/sec")
        
        return {
            'statusCode': 200,
            'batch_id': BATCH_ID,
            'predictions': len(df_results),
            'output_key': output_key,
            'elapsed_sec': round(elapsed, 2)
        }
        
    except Exception as e:
        logger.error(f"Error in prediction batch {BATCH_ID}: {str(e)}")
        raise

if __name__ == '__main__':
    main()

