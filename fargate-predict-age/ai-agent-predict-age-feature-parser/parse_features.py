#!/usr/bin/env python3
"""
Fargate Feature Parser - Parse JSON and create ML features
Reads raw training data from Athena, parses JSON in Python, saves to S3 permanently
"""

import json
import boto3
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import time
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Clients
athena_client = boto3.client('athena')
s3_client = boto3.client('s3')

# Environment variables
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'ml_predict_age')
S3_BUCKET = os.environ.get('S3_BUCKET')
WORKGROUP = os.environ.get('WORKGROUP', 'ai-agent-predict-age')

if not S3_BUCKET:
    raise ValueError("S3_BUCKET environment variable is required")

def read_from_s3_parquet(s3_prefix):
    """Read Parquet files from S3 prefix"""
    logger.info(f"Reading Parquet from s3://{S3_BUCKET}/{s3_prefix}...")
    
    # List all parquet files in the prefix
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=s3_prefix)
    
    parquet_files = []
    for page in pages:
        if 'Contents' in page:
            for obj in page['Contents']:
                # Include all files (Athena CTAS doesn't add .parquet extension)
                # Exclude directories and metadata files
                if not obj['Key'].endswith('/') and '_metadata' not in obj['Key']:
                    parquet_files.append(f"s3://{S3_BUCKET}/{obj['Key']}")
    
    logger.info(f"Found {len(parquet_files)} Parquet files")
    
    # Read all parquet files into a single DataFrame
    df = pd.read_parquet(parquet_files[0]) if len(parquet_files) == 1 else pd.concat(
        [pd.read_parquet(f) for f in parquet_files],
        ignore_index=True
    )
    
    logger.info(f"Loaded {len(df)} rows")
    return df

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
        return None
    try:
        obj = json.loads(json_str)
        if isinstance(obj, list):
            return len(obj)
    except:
        pass
    return None

def create_features(df):
    """Create all 21 ML features from raw data"""
    logger.info("Parsing JSON fields...")
    json_start = time.time()
    
    # Parse JSON fields
    df['education_level_encoded'] = df['education'].apply(parse_education_level)
    df['graduation_year'] = df['education'].apply(parse_graduation_year)
    df['number_of_jobs'] = df['work_experience'].apply(parse_json_array_length)
    df['skill_count'] = df['skills'].apply(parse_json_array_length)
    
    # Fill nulls
    df['number_of_jobs'] = df['number_of_jobs'].fillna(1)
    df['skill_count'] = df['skill_count'].fillna(5)
    
    logger.info(f"JSON parsing completed in {time.time() - json_start:.2f}s")
    
    logger.info("Creating features...")
    feature_start = time.time()
    
    # Tenure calculation
    def calc_tenure(row):
        if pd.notna(row['job_start_date']) and row['job_start_date'] != '':
            try:
                start_date = pd.to_datetime(row['job_start_date'])
                return int((datetime.now() - start_date).days / 30.44)
            except:
                pass
        if row['job_level'] == 'C-Team':
            return 120
        elif row['job_level'] == 'Manager':
            return 60
        else:
            return 36
    
    df['tenure_months'] = df.apply(calc_tenure, axis=1)
    
    # Job level encoding
    job_level_map = {'C-Team': 4, 'Manager': 3, 'Staff': 2}
    df['job_level_encoded'] = df['job_level'].map(job_level_map).fillna(1).astype(int)
    
    # Job seniority score
    def calc_seniority(title):
        if pd.isna(title):
            return 3
        title_lower = str(title).lower()
        if 'chief' in title_lower or 'vp' in title_lower:
            return 5
        elif 'senior' in title_lower or 'principal' in title_lower:
            return 4
        elif 'manager' in title_lower or 'director' in title_lower:
            return 3
        elif 'associate' in title_lower or 'analyst' in title_lower:
            return 2
        elif 'junior' in title_lower or 'entry' in title_lower:
            return 1
        else:
            return 3
    
    df['job_seniority_score'] = df['job_title'].apply(calc_seniority)
    
    # Compensation encoding
    comp_map = {
        '$200,001+': 8,
        '$150,001 - $200,000': 7,
        '$100,001 - $150,000': 6,
        '$75,001 - $100,000': 5,
        '$50,001 - $75,000': 4,
        '$25,001 - $50,000': 3
    }
    df['compensation_encoded'] = df['compensation_range'].map(comp_map).fillna(4).astype(int)
    
    # Company size encoding
    size_map = {
        '10000+': 9,
        '5000 to 9999': 8,
        '1000 to 4999': 7,
        '500 to 999': 6,
        '200 to 499': 5
    }
    df['company_size_encoded'] = df['employee_range'].astype(str).map(size_map).fillna(4).astype(int)
    
    # LinkedIn activity score
    def calc_linkedin_score(conn_count):
        try:
            count = int(conn_count) if pd.notna(conn_count) else 0
            if count > 500:
                return 1.0
            elif count > 200:
                return 0.8
            elif count > 100:
                return 0.6
            else:
                return 0.3
        except:
            return 0.3
    
    df['linkedin_activity_score'] = df['linkedin_connection_count'].apply(calc_linkedin_score)
    
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
        'Technology': 35,
        'Consulting': 38,
        'Finance': 42,
        'Healthcare': 45,
        'Education': 48,
        'Government': 50
    }
    df['industry_typical_age'] = df['industry'].astype(str).map(industry_age_map).fillna(40).astype(int)
    
    # Job function encoding
    function_map = {
        'Engineering': 1,
        'Sales': 2,
        'Marketing': 3,
        'Finance': 4,
        'Operations': 5
    }
    df['job_function_encoded'] = df['job_function'].astype(str).map(function_map).fillna(0).astype(int)
    
    # Company revenue encoding
    revenue_map = {
        '$1B+': 9,
        '$500M to $1B': 8,
        '$100M to $500M': 7
    }
    df['company_revenue_encoded'] = df['revenue_range'].astype(str).map(revenue_map).fillna(5).astype(int)
    
    # Quarter
    df['quarter'] = datetime.now().month // 3 + (1 if datetime.now().month % 3 else 0)
    
    # Total career years
    def calc_career_years(row):
        if pd.notna(row['graduation_year']):
            return max(1, 2025 - int(row['graduation_year']))
        else:
            return max(1, row['tenure_months'] / 12.0)
    
    df['total_career_years'] = df.apply(calc_career_years, axis=1)
    
    # Job churn rate
    df['job_churn_rate'] = df['number_of_jobs'] / df['total_career_years']
    df['job_churn_rate'] = df['job_churn_rate'].fillna(0.2)
    
    # Interaction features
    df['tenure_job_level_interaction'] = df['tenure_months'] * df['job_level_encoded']
    df['comp_size_interaction'] = df['compensation_encoded'] * df['company_size_encoded']
    
    df['feature_creation_date'] = datetime.now().strftime('%Y-%m-%d')
    df['feature_version'] = 'v1.0_fargate_parsed'
    
    logger.info(f"Feature engineering completed in {time.time() - feature_start:.2f}s")
    
    # Select final feature columns
    feature_cols = [
        'id', 'tenure_months', 'position_level_encoded', 'job_seniority_score',
        'compensation_encoded', 'company_size_encoded', 'linkedin_activity_score',
        'days_since_profile_update', 'social_media_presence_score', 
        'email_engagement_score', 'industry_typical_age', 'job_function_encoded',
        'company_revenue_encoded', 'quarter', 'education_level_encoded',
        'graduation_year', 'number_of_jobs', 'skill_count', 'total_career_years',
        'job_churn_rate', 'tenure_job_level_interaction', 'comp_size_interaction',
        'feature_creation_date', 'feature_version'
    ]
    
    return df[feature_cols]

def main():
    """Main function"""
    start_time = time.time()
    
    try:
        logger.info("=== Starting Fargate Feature Parser ===")
        logger.info(f"Database: {DATABASE_NAME}")
        logger.info(f"S3 Bucket: {S3_BUCKET}")
        
        # Read raw training data directly from S3
        logger.info("Reading training raw data from S3...")
        df_raw = read_from_s3_parquet('predict-age/permanent/training_raw_14m')
        
        # Parse and create features
        df_features = create_features(df_raw)
        
        # Save to S3 as Parquet
        logger.info("Saving features to S3...")
        output_path = '/tmp/training_features_parsed.parquet'
        df_features.to_parquet(output_path, index=False, compression='snappy')
        
        s3_key = 'predict-age/permanent/training_features_parsed_14m/features.parquet'
        s3_client.upload_file(output_path, S3_BUCKET, s3_key)
        
        logger.info(f"✅ Features saved to s3://{S3_BUCKET}/{s3_key}")
        logger.info(f"✅ Total time: {time.time() - start_time:.2f}s")
        logger.info(f"✅ Processed {len(df_features)} rows with {len(df_features.columns)} columns")
        
        return {
            'statusCode': 200,
            'message': 'Feature parsing completed successfully',
            'rows_processed': len(df_features),
            'columns_created': len(df_features.columns)
        }
        
    except Exception as e:
        logger.error(f"Error in feature parser: {str(e)}")
        raise

if __name__ == '__main__':
    main()

