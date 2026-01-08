import json
import boto3
import os
from datetime import datetime
import logging
import time
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import Ridge
import xgboost as xgb
import joblib
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Clients
athena_client = boto3.client('athena')
s3_client = boto3.client('s3')

# Environment variables
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'ml_predict_age')
S3_BUCKET = os.environ.get('S3_BUCKET')
WORKGROUP = os.environ.get('WORKGROUP', 'primary')

if not S3_BUCKET:
    raise ValueError("S3_BUCKET environment variable is required")

def main():
    """
    Main function to train regression models for age prediction.
    Trains 3 models: Ridge, XGBoost, and for confidence (we'll use XGBoost quantiles).
    """
    try:
        logger.info("Starting age prediction model training")

        # 1. Load training data from Athena
        logger.info("Loading training features and targets from Athena...")
        training_data = load_training_data()
        
        if not training_data:
            raise Exception("No training data found")
        
        logger.info(f"Loaded {len(training_data)} training records")

        # 2. Prepare data for models
        logger.info("Preparing data for model training...")
        X, y = prepare_training_data(training_data)
        
        # 3. Split data for validation
        logger.info("Splitting data for training and validation...")
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 4. Train Ridge Regression (baseline)
        logger.info("Training Ridge Regression model...")
        model_ridge, metrics_ridge = train_ridge_model(X_train, y_train, X_val, y_val)
        save_model_to_s3(model_ridge, 'predict-age/models/ridge_model.joblib')
        logger.info(f"Ridge MAE: {metrics_ridge['mae']:.2f} years, R²: {metrics_ridge['r2']:.3f}")
        
        # 5. Train XGBoost Regressor (primary model)
        logger.info("Training XGBoost Regressor model...")
        model_xgb, metrics_xgb = train_xgboost_model(X_train, y_train, X_val, y_val)
        save_model_to_s3(model_xgb, 'predict-age/models/xgboost_model.joblib')
        logger.info(f"XGBoost MAE: {metrics_xgb['mae']:.2f} years, R²: {metrics_xgb['r2']:.3f}")
        
        # 6. Train XGBoost for quantiles (confidence intervals)
        logger.info("Training XGBoost Quantile model for confidence intervals...")
        model_qrf, metrics_qrf = train_quantile_model(X_train, y_train, X_val, y_val)
        save_model_to_s3(model_qrf, 'predict-age/models/qrf_model.joblib')
        logger.info(f"Quantile Model MAE: {metrics_qrf['mae']:.2f} years")
        
        # 7. Save combined evaluation metrics
        combined_metrics = {
            'ridge': metrics_ridge,
            'xgboost': metrics_xgb,
            'quantile': metrics_qrf,
            'timestamp': datetime.now().isoformat()
        }
        save_evaluation_metrics(combined_metrics)

        logger.info("Model training completed successfully!")
        logger.info(f"Training records: {len(training_data)}")
        logger.info(f"Best model: XGBoost with MAE {metrics_xgb['mae']:.2f} years")
        
    except Exception as e:
        logger.error(f"Error in model training: {str(e)}")
        raise

def load_training_data():
    """Load training data from Athena"""
    try:
        # Get table names from environment variables (Fargate parsed features + targets)
        features_table = os.environ.get('FEATURES_TABLE', 'predict_age_training_features_parsed_14m')
        targets_table = os.environ.get('TARGETS_TABLE', 'predict_age_training_targets_14m')
        
        # Join features with targets
        query = f"""
        SELECT 
            f.id,
            f.tenure_months,
            f.job_level_encoded,
            f.job_seniority_score,
            f.compensation_encoded,
            f.company_size_encoded,
            f.linkedin_activity_score,
            f.days_since_profile_update,
            f.social_media_presence_score,
            f.email_engagement_score,
            f.industry_typical_age,
            f.job_function_encoded,
            f.company_revenue_encoded,
            f.quarter,
            f.education_level_encoded,
            f.graduation_year,
            f.number_of_jobs,
            f.skill_count,
            f.total_career_years,
            f.job_churn_rate,
            f.tenure_job_level_interaction,
            f.comp_size_interaction,
            t.actual_age
        FROM {DATABASE_NAME}.{features_table} f
        JOIN {DATABASE_NAME}.{targets_table} t
        ON f.id = t.id
        WHERE t.actual_age IS NOT NULL
        LIMIT 1000000
        """
        
        execution_id = execute_athena_query(query, "Loading training data")
        wait_for_query_completion(execution_id)
        
        # Get results from S3
        results_key = f'athena-results/{execution_id}.csv'
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=results_key)
        result = response['Body'].read().decode('utf-8')
        
        # Parse CSV into list of dictionaries
        lines = result.strip().split('\n')
        if len(lines) < 2:
            return []
            
        headers = [h.strip('"') for h in lines[0].split(',')]
        data = []
        
        for line in lines[1:]:
            values = [v.strip('"') for v in line.split(',')]
            if len(values) == len(headers):
                row = dict(zip(headers, values))
                data.append(row)
        
        logger.info(f"Data quality summary: {len(data)} valid records loaded")
        return data
        
    except Exception as e:
        logger.error(f"Error loading training data: {str(e)}")
        raise

def prepare_training_data(data):
    """Prepare data for model training"""
    try:
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Define feature columns (22 features for employee age prediction)
        feature_columns = [
            'tenure_months', 'job_level_encoded', 'job_seniority_score',
            'compensation_encoded', 'company_size_encoded', 'linkedin_activity_score',
            'days_since_profile_update', 'social_media_presence_score', 'email_engagement_score',
            'industry_typical_age', 'job_function_encoded', 'company_revenue_encoded',
            'quarter', 'education_level_encoded', 'graduation_year', 'number_of_jobs',
            'skill_count', 'total_career_years', 'job_churn_rate',
            'tenure_job_level_interaction', 'comp_size_interaction'
        ]
        
        # Extract features and target
        X = df[feature_columns].apply(pd.to_numeric, errors='coerce').values
        y = pd.to_numeric(df['actual_age'], errors='coerce').values
        
        # Handle any NaN values
        X = np.nan_to_num(X, nan=0.0)
        y = np.nan_to_num(y, nan=35.0)  # Default to average age
        
        logger.info(f"Prepared features shape: {X.shape}, target shape: {y.shape}")
        logger.info(f"Target age range: {np.min(y):.0f} - {np.max(y):.0f} years")
        logger.info(f"Mean age: {np.mean(y):.1f} years")
        
        return X, y
        
    except Exception as e:
        logger.error(f"Error preparing training data: {str(e)}")
        raise

def train_ridge_model(X_train, y_train, X_val, y_val):
    """Train Ridge Regression model (baseline)"""
    try:
        model = Ridge(alpha=1.0, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_val)
        metrics = evaluate_regression_model(y_val, y_pred, 'Ridge')
        
        return model, metrics
        
    except Exception as e:
        logger.error(f"Error training Ridge model: {str(e)}")
        raise

def train_xgboost_model(X_train, y_train, X_val, y_val):
    """Train XGBoost Regressor model (primary)"""
    try:
        params = {
            'objective': 'reg:squarederror',
            'eval_metric': 'mae',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'min_child_weight': 3
        }
        
        model = xgb.XGBRegressor(**params)
        
        # Train (with evaluation tracking)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        # Evaluate
        y_pred = model.predict(X_val)
        metrics = evaluate_regression_model(y_val, y_pred, 'XGBoost')
        
        return model, metrics
        
    except Exception as e:
        logger.error(f"Error training XGBoost model: {str(e)}")
        raise

def train_quantile_model(X_train, y_train, X_val, y_val):
    """Train model for quantile prediction (confidence intervals)"""
    try:
        # Train two XGBoost models for 10th and 90th percentiles
        params_lower = {
            'objective': 'reg:quantileerror',
            'quantile_alpha': 0.1,
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'random_state': 42,
            'n_jobs': -1
        }
        
        params_upper = {
            'objective': 'reg:quantileerror',
            'quantile_alpha': 0.9,
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'random_state': 42,
            'n_jobs': -1
        }
        
        model_lower = xgb.XGBRegressor(**params_lower)
        model_upper = xgb.XGBRegressor(**params_upper)
        
        model_lower.fit(X_train, y_train, verbose=False)
        model_upper.fit(X_train, y_train, verbose=False)
        
        # Package both models
        model = {'lower': model_lower, 'upper': model_upper}
        
        # Evaluate on validation set
        y_pred_lower = model_lower.predict(X_val)
        y_pred_upper = model_upper.predict(X_val)
        y_pred = (y_pred_lower + y_pred_upper) / 2  # Use midpoint for MAE
        
        metrics = evaluate_regression_model(y_val, y_pred, 'Quantile')
        metrics['avg_interval_width'] = float(np.mean(y_pred_upper - y_pred_lower))
        
        return model, metrics
        
    except Exception as e:
        logger.error(f"Error training Quantile model: {str(e)}")
        raise

def evaluate_regression_model(y_true, y_pred, model_name):
    """Evaluate regression model"""
    try:
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        
        # Calculate accuracy within N years
        acc_within_3 = np.mean(np.abs(y_true - y_pred) <= 3) * 100
        acc_within_5 = np.mean(np.abs(y_true - y_pred) <= 5) * 100
        acc_within_10 = np.mean(np.abs(y_true - y_pred) <= 10) * 100
        
        metrics = {
            "model_name": model_name,
            "model_version": "v1.0",
            "validation_records": len(y_true),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 3),
            "accuracy_within_3_years": round(acc_within_3, 1),
            "accuracy_within_5_years": round(acc_within_5, 1),
            "accuracy_within_10_years": round(acc_within_10, 1),
            "evaluation_date": datetime.now().isoformat()
        }
        
        logger.info(f"{model_name} metrics - MAE: {mae:.2f} years, RMSE: {rmse:.2f} years, R²: {r2:.3f}")
        logger.info(f"  Accuracy within 5 years: {acc_within_5:.1f}%")
        return metrics
        
    except Exception as e:
        logger.error(f"Error evaluating model: {str(e)}")
        raise

def save_model_to_s3(model, s3_key):
    """Save model to S3"""
    try:
        model_buffer = io.BytesIO()
        joblib.dump(model, model_buffer)
        model_bytes = model_buffer.getvalue()
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=model_bytes,
            ContentType='application/octet-stream'
        )
        
        logger.info(f"Model saved to s3://{S3_BUCKET}/{s3_key}")
        
    except Exception as e:
        logger.error(f"Error saving model to S3: {str(e)}")
        raise

def save_evaluation_metrics(metrics):
    """Save evaluation metrics to S3"""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key='predict-age/evaluation/evaluation_metrics.json',
            Body=json.dumps(metrics, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Evaluation metrics saved to S3")
        
    except Exception as e:
        logger.error(f"Error saving evaluation metrics: {str(e)}")
        raise

def execute_athena_query(query, description):
    """Execute Athena query and return execution ID"""
    try:
        response = athena_client.start_query_execution(
            QueryString=query,
            WorkGroup=WORKGROUP,
            ResultConfiguration={
                'OutputLocation': f's3://{S3_BUCKET}/athena-results/'
            }
        )
        execution_id = response['QueryExecutionId']
        logger.info(f"{description} - Execution ID: {execution_id}")
        return execution_id
    except Exception as e:
        logger.error(f"Error executing Athena query: {str(e)}")
        raise

def wait_for_query_completion(execution_id, max_wait_time=900):
    """Wait for Athena query to complete"""
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        response = athena_client.get_query_execution(QueryExecutionId=execution_id)
        status = response['QueryExecution']['Status']['State']
        if status == 'SUCCEEDED':
            logger.info(f"Query {execution_id} completed successfully")
            return True
        elif status == 'FAILED':
            error_reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
            raise Exception(f"Query {execution_id} failed: {error_reason}")
        elif status == 'CANCELLED':
            raise Exception(f"Query {execution_id} was cancelled")
        time.sleep(5)
    raise Exception(f"Query {execution_id} timed out after {max_wait_time} seconds")

if __name__ == "__main__":
    main()

