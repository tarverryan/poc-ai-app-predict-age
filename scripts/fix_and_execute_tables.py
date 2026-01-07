#!/usr/bin/env python3
"""
Fix and execute SQL files with CTE structure to handle tenure_months references
"""
import re
import subprocess
import json
import sys

def strip_comments_and_build_sql(filename):
    """Read SQL file, strip comments, and extract CREATE TABLE structure"""
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Extract SQL lines only (no comments)
    sql_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip comment-only lines
        if stripped.startswith('--'):
            continue
        # Remove inline comments
        if '--' in line:
            comment_pos = line.find('--')
            # Only remove if not in a string
            before_comment = line[:comment_pos]
            if "'" not in before_comment or before_comment.count("'") % 2 == 0:
                line = before_comment.rstrip()
        if line.strip():
            sql_lines.append(line.rstrip())
    
    sql_text = ' '.join(sql_lines)
    
    # Find CREATE TABLE ... AS SELECT
    create_match = re.search(r'(CREATE TABLE[^)]+\)\s+AS)\s+(SELECT)', sql_text, re.IGNORECASE)
    if not create_match:
        return None, "Could not find CREATE TABLE AS SELECT pattern"
    
    create_part_end = create_match.end(1)  # End of "AS"
    select_start = create_match.end(2)  # Start of SELECT content
    
    create_part = sql_text[:create_part_end].strip()
    select_part = sql_text[select_start:].strip()
    
    # Find FROM clause
    from_match = re.search(r'\sFROM\s+([^\s]+\.[^\s]+)', select_part, re.IGNORECASE)
    if not from_match:
        return None, "Could not find FROM clause"
    
    from_table = from_match.group(1)
    from_pos = from_match.start()
    
    # Find WHERE clause
    where_match = re.search(r'\sWHERE\s+(.+)', select_part, re.IGNORECASE)
    if where_match:
        where_clause = where_match.group(1).rstrip(';').strip()
        select_cols = select_part[:where_match.start()].strip()
    else:
        where_clause = ""
        select_cols = select_part[:from_pos].strip()
    
    # Get SELECT column list (everything before FROM, but after SELECT keyword)
    select_list = select_cols.replace('SELECT', '', 1).strip()
    
    # Build CTE version
    fixed_sql = f"""{create_part}
WITH base_features AS (
SELECT
{select_list}
FROM {from_table}
{f'WHERE {where_clause}' if where_clause else ''}
)
SELECT * FROM base_features"""
    
    return fixed_sql, None

def execute_athena_query(sql, description):
    """Execute Athena query and return execution ID"""
    import os
    s3_bucket = os.environ.get('S3_BUCKET')
    database = os.environ.get('DATABASE_NAME', 'ml_predict_age')
    workgroup = os.environ.get('WORKGROUP', 'primary')
    region = os.environ.get('AWS_REGION', 'us-east-1')
    
    if not s3_bucket:
        raise ValueError("S3_BUCKET environment variable is required")
    
    try:
        result = subprocess.run([
            'aws', 'athena', 'start-query-execution',
            '--query-string', sql,
            '--query-execution-context', f'Database={database}',
            '--result-configuration', f'OutputLocation=s3://{s3_bucket}/athena-results/',
            '--work-group', workgroup,
            '--region', region,
            '--output', 'json'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data['QueryExecutionId'], None
        else:
            error = result.stderr[:500] if result.stderr else result.stdout[:500]
            return None, error
    except Exception as e:
        return None, str(e)

def main():
    files = [
        ('sql/03_ai_agent_kb_predict_age_predict_age_real_training_features_14m.sql', 'Training Features'),
        ('sql/05_ai_agent_kb_predict_age_predict_age_full_evaluation_features_378m.sql', 'Evaluation Features')
    ]
    
    print("=== Fixing and Executing SQL Files ===\n")
    
    for sql_file, name in files:
        print(f"Processing: {name}")
        print(f"  File: {sql_file}")
        
        # Fix SQL
        fixed_sql, error = strip_comments_and_build_sql(sql_file)
        if error:
            print(f"  ❌ Error fixing SQL: {error}")
            continue
        
        # Clean up whitespace
        fixed_sql = re.sub(r'\s+', ' ', fixed_sql)
        fixed_sql = re.sub(r'\s+', ' ', fixed_sql.replace('\n', ' '))
        
        print(f"  SQL length: {len(fixed_sql)}")
        
        # Execute
        exec_id, error = execute_athena_query(fixed_sql, name)
        if exec_id:
            print(f"  ✅ Query started: {exec_id}")
        else:
            print(f"  ❌ Error: {error}")
        print()

if __name__ == '__main__':
    main()

