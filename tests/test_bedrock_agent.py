#!/usr/bin/env python3
"""
Bedrock Agent Testing Script
Tests the predict-age-agent systematically through all query categories
"""

import boto3
import json
import time
from datetime import datetime

# Agent configuration
AGENT_ID = "XIGMZVBUV8"
AGENT_ALIAS_ID = "TSTALIASID"
REGION = "us-east-1"

# Initialize client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

def invoke_agent(query, session_id=None):
    """Invoke the Bedrock Agent with a query"""
    if session_id is None:
        session_id = f"test-{int(time.time())}"
    
    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=query
        )
        
        # Stream and collect the response
        answer = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk_data = event['chunk']
                if 'bytes' in chunk_data:
                    answer += chunk_data['bytes'].decode('utf-8')
        
        return answer.strip()
    
    except Exception as e:
        return f"ERROR: {str(e)}"

def score_response(query, response, expected_keywords=None):
    """Score the response on a 0-5 scale"""
    if "ERROR" in response:
        return 0, "Error occurred"
    
    if len(response) < 50:
        return 1, "Response too short"
    
    score = 3  # Base score for any reasonable response
    notes = []
    
    # Check for expected keywords
    if expected_keywords:
        found = sum(1 for kw in expected_keywords if kw.lower() in response.lower())
        if found >= len(expected_keywords) * 0.8:
            score += 1
            notes.append(f"Found {found}/{len(expected_keywords)} keywords")
        elif found >= len(expected_keywords) * 0.5:
            notes.append(f"Found {found}/{len(expected_keywords)} keywords")
        else:
            score -= 1
            notes.append(f"Only found {found}/{len(expected_keywords)} keywords")
    
    # Check for SQL code if query asks for it
    if "sql" in query.lower() or "query" in query.lower():
        if "SELECT" in response and "FROM" in response:
            score += 1
            notes.append("Provided SQL code")
        else:
            score -= 1
            notes.append("Missing SQL code")
    
    # Check for specific metrics if asking about performance
    if "accurate" in query.lower() or "mae" in query.lower() or "performance" in query.lower():
        if "2.23" in response or "0.739" in response:
            score += 1
            notes.append("Cited specific metrics")
    
    # Cap score at 5
    score = min(5, max(0, score))
    
    return score, "; ".join(notes) if notes else "Standard response"

# Test queries organized by category
TEST_QUERIES = [
    # Category 1: Model Performance (5 tests)
    {
        "category": "Model Performance",
        "query": "What's the model accuracy? What's the MAE?",
        "expected": ["2.23", "MAE", "years", "0.739", "R²"]
    },
    {
        "category": "Model Performance",
        "query": "How accurate are the predictions? What percentage are within 5 years?",
        "expected": ["75%", "within", "5 years", "95%"]
    },
    {
        "category": "Model Performance",
        "query": "Why was XGBoost chosen over other models?",
        "expected": ["XGBoost", "Ridge", "28%", "better", "MAE"]
    },
    {
        "category": "Model Performance",
        "query": "Does accuracy vary by age group? Which age ranges are best?",
        "expected": ["25-45", "best", "age group", "35-44"]
    },
    {
        "category": "Model Performance",
        "query": "What models were trained and which is in production?",
        "expected": ["XGBoost", "Ridge", "Quantile", "production"]
    },
    
    # Category 2: Confidence Scores (5 tests)
    {
        "category": "Confidence Scores",
        "query": "What's the difference between confidence_score_original and confidence_pct?",
        "expected": ["dual", "original", "interval", "percentage", "0-100"]
    },
    {
        "category": "Confidence Scores",
        "query": "Why are some confidence scores negative? Is that an error?",
        "expected": ["negative", "excellent", "quantile", "crossing", "not error"]
    },
    {
        "category": "Confidence Scores",
        "query": "What confidence threshold should I use for email marketing?",
        "expected": ["80%", "email", "personalized", "high confidence"]
    },
    {
        "category": "Confidence Scores",
        "query": "What's the average confidence score? How many PIDs are high quality?",
        "expected": ["83%", "high quality", "60%", "314"]
    },
    {
        "category": "Confidence Scores",
        "query": "Can I use predictions for legal compliance or age-restricted content?",
        "expected": ["no", "never", "100%", "real data", "legal"]
    },
    
    # Category 3: SQL Queries (5 tests)
    {
        "category": "SQL Queries",
        "query": "Show me SQL to query the age predictions table for ages 30-40",
        "expected": ["SELECT", "FROM", "predict_age", "WHERE", "BETWEEN 30 AND 40"]
    },
    {
        "category": "SQL Queries",
        "query": "Give me SQL to filter by confidence score above 60%",
        "expected": ["SELECT", "confidence_pct", "WHERE", ">= 60"]
    },
    {
        "category": "SQL Queries",
        "query": "How do I segment by age ranges like Millennials vs Gen X?",
        "expected": ["SELECT", "CASE", "WHEN", "28-43", "44-59"]
    },
    {
        "category": "SQL Queries",
        "query": "Show me SQL for confidence distribution analysis",
        "expected": ["SELECT", "confidence", "COUNT", "GROUP BY"]
    },
    {
        "category": "SQL Queries",
        "query": "How do I join age predictions with my employee table?",
        "expected": ["JOIN", "ON", "pid", "predict_age_final_results"]
    },
    
    # Category 4: Data Schema (3 tests)
    {
        "category": "Data Schema",
        "query": "What's the schema for the predictions table? What columns are available?",
        "expected": ["pid", "predicted_age", "confidence", "prediction_source"]
    },
    {
        "category": "Data Schema",
        "query": "How many PIDs have predictions? What's ML vs real data?",
        "expected": ["378", "million", "37.5%", "62.5%", "141.7", "236"]
    },
    {
        "category": "Data Schema",
        "query": "Where is the data stored? What's the S3 path?",
        "expected": ["S3", "${S3_BUCKET}", "predict-age"]
    },
    
    # Category 5: Features (4 tests)
    {
        "category": "Features",
        "query": "What features does the model use? How many are there?",
        "expected": ["22", "features", "tenure", "job_level", "linkedin"]
    },
    {
        "category": "Features",
        "query": "What's the most important feature for predicting age?",
        "expected": ["total_career_years", "23.4%", "most important"]
    },
    {
        "category": "Features",
        "query": "What are the top 5 features?",
        "expected": ["total_career_years", "tenure_months", "job_level", "education"]
    },
    {
        "category": "Features",
        "query": "How is total_career_years calculated?",
        "expected": ["work_experience", "tenure", "education", "calculated"]
    },
    
    # Category 6: Cost & Performance (4 tests)
    {
        "category": "Cost & Performance",
        "query": "How much does it cost to run the pipeline?",
        "expected": ["$15", "per run", "$60", "year", "quarterly"]
    },
    {
        "category": "Cost & Performance",
        "query": "How long does the pipeline take to run?",
        "expected": ["45", "minutes", "25", "training"]
    },
    {
        "category": "Cost & Performance",
        "query": "What are the main cost drivers?",
        "expected": ["Fargate", "prediction", "92%", "cost"]
    },
    {
        "category": "Cost & Performance",
        "query": "How can I reduce costs for Athena queries?",
        "expected": ["WHERE", "LIMIT", "filter", "partition"]
    },
    
    # Category 7: Architecture (3 tests)
    {
        "category": "Architecture",
        "query": "How does the pipeline work? What are the main stages?",
        "expected": ["Step Functions", "8", "stages", "Fargate", "Lambda"]
    },
    {
        "category": "Architecture",
        "query": "How many Fargate tasks run in parallel?",
        "expected": ["898", "500", "concurrent", "parallel"]
    },
    {
        "category": "Architecture",
        "query": "What AWS services are used?",
        "expected": ["Fargate", "Lambda", "Athena", "S3", "Step Functions"]
    },
    
    # Category 8: Business Use Cases (3 tests)
    {
        "category": "Business Use Cases",
        "query": "What can I use age predictions for?",
        "expected": ["marketing", "segmentation", "CRM", "enrichment"]
    },
    {
        "category": "Business Use Cases",
        "query": "What's the best confidence threshold for marketing campaigns?",
        "expected": ["60%", "80%", "personalized", "segmentation"]
    },
    {
        "category": "Business Use Cases",
        "query": "Should I use exact ages or age ranges?",
        "expected": ["ranges", "not exact", "30-40", "better"]
    },
    
    # Category 9: Troubleshooting (3 tests)
    {
        "category": "Troubleshooting",
        "query": "Why am I getting a type mismatch error on pid?",
        "expected": ["BIGINT", "VARCHAR", "CAST", "type"]
    },
    {
        "category": "Troubleshooting",
        "query": "My query timed out, what should I do?",
        "expected": ["WHERE", "LIMIT", "filter", "timeout"]
    },
    {
        "category": "Troubleshooting",
        "query": "Why do some PIDs have low confidence scores?",
        "expected": ["sparse", "profile", "features", "missing"]
    },
]

def run_tests():
    """Run all test queries and generate report"""
    print("="*80)
    print(f"BEDROCK AGENT TEST REPORT")
    print(f"Agent ID: {AGENT_ID}")
    print(f"Agent Alias: {AGENT_ALIAS_ID}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print()
    
    results = []
    category_scores = {}
    
    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n[{i}/{len(TEST_QUERIES)}] Category: {test['category']}")
        print(f"Query: {test['query']}")
        print("-"*80)
        
        # Invoke agent
        start_time = time.time()
        response = invoke_agent(test['query'])
        elapsed = time.time() - start_time
        
        # Score response
        score, notes = score_response(test['query'], response, test.get('expected'))
        
        # Store result
        result = {
            "category": test['category'],
            "query": test['query'],
            "response": response,
            "score": score,
            "notes": notes,
            "elapsed": elapsed
        }
        results.append(result)
        
        # Update category scores
        if test['category'] not in category_scores:
            category_scores[test['category']] = []
        category_scores[test['category']].append(score)
        
        # Print result
        print(f"Response ({elapsed:.1f}s): {response[:200]}{'...' if len(response) > 200 else ''}")
        print(f"Score: {score}/5 - {notes}")
        
        # Brief pause between requests
        time.sleep(2)
    
    # Generate summary
    print("\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)
    
    total_score = sum(r['score'] for r in results)
    max_score = len(results) * 5
    avg_score = total_score / len(results)
    
    print(f"\nOverall Performance:")
    print(f"  Total Score: {total_score}/{max_score} ({total_score/max_score*100:.1f}%)")
    print(f"  Average Score: {avg_score:.2f}/5.00")
    print(f"  Tests Passed (≥4): {sum(1 for r in results if r['score'] >= 4)}/{len(results)}")
    
    print(f"\nBy Category:")
    for category, scores in sorted(category_scores.items()):
        avg = sum(scores) / len(scores)
        print(f"  {category}: {avg:.2f}/5.00 ({len(scores)} tests)")
    
    print(f"\nTop Performing Queries:")
    top_results = sorted(results, key=lambda x: x['score'], reverse=True)[:5]
    for r in top_results:
        print(f"  [{r['score']}/5] {r['query'][:60]}...")
    
    print(f"\nNeeds Improvement:")
    low_results = sorted(results, key=lambda x: x['score'])[:5]
    for r in low_results:
        print(f"  [{r['score']}/5] {r['query'][:60]}...")
        print(f"    Issue: {r['notes']}")
    
    # Save detailed results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"agent_test_results_{timestamp}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_file}")
    
    print("\n" + "="*80)
    print(f"Testing completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    return avg_score >= 4.0  # Pass if average score >= 4.0

if __name__ == "__main__":
    try:
        success = run_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        exit(1)

