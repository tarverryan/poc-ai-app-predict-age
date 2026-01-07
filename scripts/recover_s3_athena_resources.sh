#!/bin/bash

################################################################################
# Recovery Script: Restore S3 and Athena Resources for Age Prediction Pipeline
################################################################################
#
# This script regenerates all deleted S3 data and Athena tables from source.
# Source table: Configure via SOURCE_DATABASE and SOURCE_TABLE environment variables
# Example: SOURCE_DATABASE=source_db SOURCE_TABLE=source_table_2025q3
#
# Recovery Order (dependency chain):
#   1. Database (verify exists)
#   2. Staging parsed features (from source)
#   3. Training features (from staging)
#   4. Training targets (from source)
#   5. Full evaluation features (from staging)
#   6. Predictions table (created by Lambda, but we verify)
#   7. Human QA table (created by Lambda)
#   8. Final results table (created by Lambda)
#
# Estimated Time: 45-60 minutes
# Estimated Cost: $0.60-0.70
################################################################################

set -e  # Exit on error

# Configuration
# NOTE: Set S3_BUCKET environment variable before running this script
REGION="${AWS_REGION:-us-east-1}"
DATABASE="${DATABASE_NAME:-ml_predict_age}"
WORKGROUP="${WORKGROUP:-primary}"
S3_BUCKET="${S3_BUCKET}"
S3_BASE="s3://${S3_BUCKET}/predict-age"
ATHENA_RESULTS="s3://${S3_BUCKET}/athena-results"
SOURCE_DATABASE="${SOURCE_DATABASE:-source_database}"
SOURCE_TABLE="${SOURCE_TABLE:-source_table_2025q3}"
SOURCE_TABLE_FULL="${SOURCE_DATABASE}.${SOURCE_TABLE}"
SQL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../sql" && pwd)"

# Validate required environment variables
if [ -z "$S3_BUCKET" ]; then
    echo "ERROR: S3_BUCKET environment variable is required"
    echo "Usage: S3_BUCKET=your-bucket-name [SOURCE_DATABASE=source_db] [SOURCE_TABLE=source_table] $0"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Execute Athena query and wait for completion
execute_athena_query() {
    local query="$1"
    local description="$2"
    
    log_info "Executing: $description"
    
    # Start query
    local execution_id=$(aws athena start-query-execution \
        --query-string "$query" \
        --query-execution-context "Database=${DATABASE}" \
        --result-configuration "OutputLocation=${ATHENA_RESULTS}/" \
        --work-group "${WORKGROUP}" \
        --region "${REGION}" \
        --output text --query 'QueryExecutionId')
    
    log_info "Query started: ${execution_id}"
    
    # Wait for completion
    while true; do
        local status=$(aws athena get-query-execution \
            --query-execution-id "${execution_id}" \
            --region "${REGION}" \
            --output text --query 'QueryExecution.Status.State')
        
        if [ "$status" = "SUCCEEDED" ]; then
            log_success "Query completed: ${execution_id}"
            return 0
        elif [ "$status" = "FAILED" ]; then
            local reason=$(aws athena get-query-execution \
                --query-execution-id "${execution_id}" \
                --region "${REGION}" \
                --output text --query 'QueryExecution.Status.StateChangeReason')
            log_error "Query failed: ${reason}"
            return 1
        elif [ "$status" = "CANCELLED" ]; then
            log_error "Query was cancelled"
            return 1
        fi
        
        sleep 10
    done
}

# Verify source table exists
verify_source_table() {
    log_info "Verifying source table exists..."
    
    if aws athena get-table-metadata \
        --catalog-name AwsDataCatalog \
        --database-name "${SOURCE_DATABASE}" \
        --table-name "${SOURCE_TABLE}" \
        --region "${REGION}" \
        > /dev/null 2>&1; then
        log_success "Source table exists: ${SOURCE_TABLE_FULL}"
        return 0
    else
        log_error "Source table NOT FOUND: ${SOURCE_TABLE_FULL}"
        log_error "Cannot proceed without source data!"
        log_error "Set SOURCE_DATABASE and SOURCE_TABLE environment variables"
        return 1
    fi
}

# Verify database exists
verify_database() {
    log_info "Verifying database exists..."
    
    if aws athena get-database \
        --catalog-name AwsDataCatalog \
        --database-name "${DATABASE}" \
        --region "${REGION}" \
        > /dev/null 2>&1; then
        log_success "Database exists: ${DATABASE}"
        return 0
    else
        log_warning "Database does not exist. Creating..."
        
        local create_db_query="CREATE DATABASE IF NOT EXISTS ${DATABASE} COMMENT 'Age prediction ML pipeline - training and evaluation' LOCATION '${S3_BASE}/';"
        
        aws athena start-query-execution \
            --query-string "$create_db_query" \
            --result-configuration "OutputLocation=${ATHENA_RESULTS}/" \
            --work-group "${WORKGROUP}" \
            --region "${REGION}" \
            > /dev/null
        
        log_success "Database created: ${DATABASE}"
        return 0
    fi
}

# Check if S3 path has data
check_s3_data() {
    local s3_path="$1"
    local count=$(aws s3 ls "${s3_path}/" --recursive 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$count" -gt 0 ]; then
        return 0  # Data exists
    else
        return 1  # No data
    fi
}

# Check if Athena table exists and has data
# Returns: 0 = table and data exist, 1 = table doesn't exist, 2 = table exists but no data
check_athena_table() {
    local table_name="$1"
    local s3_path="$2"
    
    # Check if table exists
    if ! aws athena get-table-metadata \
        --catalog-name AwsDataCatalog \
        --database-name "${DATABASE}" \
        --table-name "${table_name}" \
        --region "${REGION}" \
        > /dev/null 2>&1; then
        echo 1  # Table doesn't exist
        return
    fi
    
    # Check if S3 has data
    if check_s3_data "${s3_path}"; then
        echo 0  # Table and data exist
    else
        echo 2  # Table exists but no data
    fi
}

# Recreate table from SQL file
recreate_table_from_sql() {
    local sql_file="$1"
    local table_name="$2"
    local description="$3"
    
    if [ ! -f "${sql_file}" ]; then
        log_error "SQL file not found: ${sql_file}"
        return 1
    fi
    
    log_info "Recreating table: ${table_name}"
    
    local query=$(cat "${sql_file}")
    
    if execute_athena_query "$query" "$description"; then
        log_success "Table recreated: ${table_name}"
        return 0
    else
        log_error "Failed to recreate table: ${table_name}"
        return 1
    fi
}

# Main recovery function
main() {
    echo ""
    echo "================================================================================"
    echo "AGE PREDICTION PIPELINE - S3/ATHENA RECOVERY"
    echo "================================================================================"
    echo ""
    echo "This script will regenerate all deleted S3 data and Athena tables."
    echo "Source: ${SOURCE_TABLE_FULL}"
    echo "Target Database: ${DATABASE}"
    echo ""
    if [ "${NON_INTERACTIVE}" != "true" ]; then
        read -p "Continue? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_warning "Recovery cancelled"
            exit 0
        fi
        echo ""
    else
        log_info "Non-interactive mode: Auto-confirming..."
        echo ""
    fi
    
    # Step 1: Verify prerequisites
    log_info "=== STEP 1: Verifying Prerequisites ==="
    verify_source_table || exit 1
    verify_database || exit 1
    echo ""
    
    # Step 2: Recreate Staging Table (from source)
    log_info "=== STEP 2: Recreating Staging Table ==="
    local staging_table="predict_age_staging_parsed_features_2025q3"
    local staging_s3="${S3_BASE}/${staging_table}/"
    local staging_sql="${SQL_DIR}/02_ai_agent_kb_predict_age_${staging_table}.sql"
    
    local staging_status=$(check_athena_table "${staging_table}" "${staging_s3}")
    if [ "$staging_status" -eq 0 ]; then
        log_success "Staging table exists with data. Skipping."
    elif [ "$staging_status" -eq 2 ]; then
        log_warning "Staging table exists but has no data. Recreating..."
        recreate_table_from_sql "${staging_sql}" "${staging_table}" "Staging parsed features (378M rows, ~15-20 min)"
    else
        recreate_table_from_sql "${staging_sql}" "${staging_table}" "Staging parsed features (378M rows, ~15-20 min)"
    fi
    echo ""
    
    # Step 3: Recreate Training Features (from staging)
    log_info "=== STEP 3: Recreating Training Features ==="
    local train_features_table="predict_age_real_training_features_14m"
    local train_features_s3="${S3_BASE}/${train_features_table}/"
    local train_features_sql="${SQL_DIR}/03_ai_agent_kb_predict_age_${train_features_table}.sql"
    
    local train_features_status=$(check_athena_table "${train_features_table}" "${train_features_s3}")
    if [ "$train_features_status" -eq 0 ]; then
        log_success "Training features table exists with data. Skipping."
    elif [ "$train_features_status" -eq 2 ]; then
        log_warning "Training features table exists but has no data. Recreating..."
        recreate_table_from_sql "${train_features_sql}" "${train_features_table}" "Training features (14M rows, ~3-5 min)"
    else
        recreate_table_from_sql "${train_features_sql}" "${train_features_table}" "Training features (14M rows, ~3-5 min)"
    fi
    echo ""
    
    # Step 4: Recreate Training Targets (from source)
    log_info "=== STEP 4: Recreating Training Targets ==="
    local train_targets_table="predict_age_real_training_targets_14m"
    local train_targets_s3="${S3_BASE}/${train_targets_table}/"
    local train_targets_sql="${SQL_DIR}/04_ai_agent_kb_predict_age_${train_targets_table}.sql"
    
    local train_targets_status=$(check_athena_table "${train_targets_table}" "${train_targets_s3}")
    if [ "$train_targets_status" -eq 0 ]; then
        log_success "Training targets table exists with data. Skipping."
    elif [ "$train_targets_status" -eq 2 ]; then
        log_warning "Training targets table exists but has no data. Recreating..."
        recreate_table_from_sql "${train_targets_sql}" "${train_targets_table}" "Training targets (14M rows, ~2-3 min)"
    else
        recreate_table_from_sql "${train_targets_sql}" "${train_targets_table}" "Training targets (14M rows, ~2-3 min)"
    fi
    echo ""
    
    # Step 5: Recreate Full Evaluation Features (from staging)
    log_info "=== STEP 5: Recreating Full Evaluation Features ==="
    local eval_features_table="predict_age_full_evaluation_features_378m"
    local eval_features_s3="${S3_BASE}/${eval_features_table}/"
    local eval_features_sql="${SQL_DIR}/05_ai_agent_kb_predict_age_${eval_features_table}.sql"
    
    local eval_features_status=$(check_athena_table "${eval_features_table}" "${eval_features_s3}")
    if [ "$eval_features_status" -eq 0 ]; then
        log_success "Evaluation features table exists with data. Skipping."
    elif [ "$eval_features_status" -eq 2 ]; then
        log_warning "Evaluation features table exists but has no data. Recreating..."
        recreate_table_from_sql "${eval_features_sql}" "${eval_features_table}" "Full evaluation features (378M rows, ~12-15 min)"
    else
        recreate_table_from_sql "${eval_features_sql}" "${eval_features_table}" "Full evaluation features (378M rows, ~12-15 min)"
    fi
    echo ""
    
    # Step 6: Note about Lambda-created tables
    log_info "=== STEP 6: Lambda-Created Tables ==="
    log_info "The following tables are created by Lambda functions during pipeline execution:"
    log_info "  - predict_age_predictions_2025q3 (created by CreatePredictionsTable Lambda)"
    log_info "  - predict_age_human_qa_2025q3 (created by HumanQA Lambda)"
    log_info "  - predict_age_final_results_2025q3 (created by FinalResults Lambda)"
    log_warning "These will be recreated when you run the Step Functions pipeline."
    echo ""
    
    # Step 7: Verify raw source tables (these might still exist)
    log_info "=== STEP 7: Checking Raw Source Tables ==="
    local raw_tables=(
        "predict_age_full_evaluation_raw_378m"
        "predict_age_training_raw_14m"
        "predict_age_training_targets_14m"
    )
    
    for table in "${raw_tables[@]}"; do
        if aws athena get-table-metadata \
            --catalog-name AwsDataCatalog \
            --database-name "${DATABASE}" \
            --table-name "${table}" \
            --region "${REGION}" \
            > /dev/null 2>&1; then
            local table_s3="${S3_BASE}/${table}/"
            if check_s3_data "${table_s3}"; then
                log_success "Raw table exists with data: ${table}"
            else
                log_warning "Raw table exists but has no data: ${table} (may need regeneration)"
            fi
        else
            log_info "Raw table does not exist: ${table} (will be created by pipeline if needed)"
        fi
    done
    echo ""
    
    # Summary
    echo "================================================================================"
    log_success "RECOVERY COMPLETE!"
    echo "================================================================================"
    echo ""
    echo "✅ Base tables regenerated from source"
    echo "⚠️  Models need to be retrained (run training Step Functions)"
    echo "⚠️  Predictions need to be regenerated (run full pipeline)"
    echo ""
    echo "Next steps:"
    echo "  1. Run training: Step Functions execution for training stage"
    echo "  2. Run full pipeline: Step Functions execution for complete pipeline"
    echo ""
}

# Run main function
main

