-- SQL Query to Join All Tables Together
-- This query joins all the final results tables from different prediction models
-- All joins are INNER JOINs on pid to return only records present in all tables
-- All y/n flags are lowercased, all score fields formatted as percentages (0.00% to 100.00%)

SELECT 
    -- Common identifier
    CAST(job_title.pid AS BIGINT) as pid,
    
    -- Job Title & Org Name Changes (flags: lowercase y/n, scores: 0.00% to 100.00%)
    LOWER(CAST(job_title.job_title_change_flag AS VARCHAR)) as job_title_change_flag,
    CAST(ROUND(CAST(job_title.job_title_change_score AS DOUBLE) * 100.0, 2) AS DECIMAL(10,2)) as job_title_change_score,
    LOWER(CAST(job_title.org_name_change_flag AS VARCHAR)) as org_name_change_flag,
    CAST(ROUND(CAST(job_title.org_name_change_score AS DOUBLE) * 100.0, 2) AS DECIMAL(10,2)) as org_name_change_score,
    LOWER(CAST(job_title.job_title_org_name_change_flag AS VARCHAR)) as job_title_org_name_change_flag,
    CAST(ROUND(CAST(job_title.job_title_org_name_change_score AS DOUBLE) * 100.0, 2) AS DECIMAL(10,2)) as job_title_org_name_change_score,
    
    -- Job Change Predictions (flags: lowercase y/n, scores: 0.00% to 100.00%)
    LOWER(CAST(job_change.job_change_prediction AS VARCHAR)) as job_change_prediction,
    CAST(ROUND(CAST(job_change.job_change_prediction_score AS DOUBLE) * 100.0, 2) AS DECIMAL(10,2)) as job_change_prediction_score,
    
    -- Age Predictions (scores: 0.00% to 100.00%)
    -- Note: age.confidence_score is already on 0-100 scale, so just round to 2 decimals
    age.predicted_age,
    CAST(ROUND(CAST(age.confidence_score AS DOUBLE), 2) AS DECIMAL(10,2)) as age_confidence_score,
    
    -- Sex Predictions (scores: 0.00% to 100.00%)
    sex.sex_mf_prediction,
    CAST(ROUND(CAST(sex.sex_mf_prediction_score AS DOUBLE) * 100.0, 2) AS DECIMAL(10,2)) as sex_mf_prediction_score,
    
    -- Compensation Predictions (scores: 0.00% to 100.00%)
    compensation.compensation_prediction,
    CAST(ROUND(CAST(compensation.compensation_prediction_score AS DOUBLE) * 100.0, 2) AS DECIMAL(10,2)) as compensation_prediction_score,
    
    -- High Value Contacts (flags: lowercase y/n, scores: 0.00% to 100.00%)
    -- Note: high_value_contact_score is already on 0-100 scale, so just round to 2 decimals
    LOWER(CAST(hvc.high_value_contact AS VARCHAR)) as high_value_contact,
    CAST(ROUND(CAST(hvc.high_value_contact_score AS DOUBLE), 2) AS DECIMAL(10,2)) as high_value_contact_score,
    
    -- Contact Quality Score (0.00% to 100.00%)
    -- Note: contact_quality_score is already on 0-100 scale, so just round to 2 decimals
    CAST(ROUND(CAST(quality.contact_quality_score AS DOUBLE), 2) AS DECIMAL(10,2)) as contact_quality_score

FROM "ai_agent_kb_job_title_org_name"."job_title_org_name_2025q2_2025q3_final" job_title

-- Join Job Change Predictions
INNER JOIN "ai_agent_kb_predict_job_change"."predict_job_change_final_results_2025q3" job_change
    ON CAST(job_title.pid AS BIGINT) = CAST(job_change.pid AS BIGINT)

-- Join Age Predictions
INNER JOIN "${DATABASE_NAME}"."predict_age_final_results_2025q3" age
    ON CAST(job_title.pid AS BIGINT) = CAST(age.pid AS BIGINT)

-- Join Sex Predictions
INNER JOIN "ai_agent_kb_predict_sex"."predict_sex_final_results_2025q3" sex
    ON CAST(job_title.pid AS BIGINT) = CAST(sex.pid AS BIGINT)

-- Join Compensation Predictions
INNER JOIN "ai_agent_kb_predict_compensation"."predict_compensation_final_results_2025q3" compensation
    ON CAST(job_title.pid AS BIGINT) = CAST(compensation.pid AS BIGINT)

-- Join High Value Contacts
INNER JOIN "ai_agent_kb_high_value_contacts"."high_value_contacts_2025q3_final" hvc
    ON CAST(job_title.pid AS BIGINT) = CAST(hvc.pid AS BIGINT)

-- Join Contact Quality Score
INNER JOIN "ai_agent_kb_quality_score_contacts"."quality_score_contacts_2025q3_final" quality
    ON CAST(job_title.pid AS BIGINT) = CAST(quality.pid AS BIGINT)

-- Optional: Add WHERE clause to filter specific PIDs or conditions
-- WHERE job_title.pid = 12345;
-- WHERE age.predicted_age IS NOT NULL;

