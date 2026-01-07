-- Test query: Validate JSON parsing works correctly
-- Run this manually in Athena console to verify before creating full staging table
-- Expected: 10 rows with parsed education_level, job_count, skill_count

SELECT 
    pid,
    
    -- Test education parsing
    CASE 
        WHEN education IS NOT NULL AND education != '' AND education != '[]' THEN
            CASE 
                WHEN LOWER(COALESCE(TRY(CAST(json_extract(json_parse(education), '$[0].degrees[0]') AS VARCHAR)), '')) LIKE '%phd%' 
                  OR LOWER(COALESCE(TRY(CAST(json_extract(json_parse(education), '$[0].degrees[0]') AS VARCHAR)), '')) LIKE '%doctorate%' THEN 5
                WHEN LOWER(COALESCE(TRY(CAST(json_extract(json_parse(education), '$[0].degrees[0]') AS VARCHAR)), '')) LIKE '%master%'
                  OR LOWER(COALESCE(TRY(CAST(json_extract(json_parse(education), '$[0].degrees[0]') AS VARCHAR)), '')) LIKE '%mba%' THEN 4
                WHEN LOWER(COALESCE(TRY(CAST(json_extract(json_parse(education), '$[0].degrees[0]') AS VARCHAR)), '')) LIKE '%bachelor%' THEN 3
                WHEN LOWER(COALESCE(TRY(CAST(json_extract(json_parse(education), '$[0].degrees[0]') AS VARCHAR)), '')) LIKE '%associate%' THEN 2
                WHEN LOWER(COALESCE(TRY(CAST(json_extract(json_parse(education), '$[0].degrees[1]') AS VARCHAR)), '')) LIKE '%bachelor%' THEN 3
                ELSE 1
            END
        ELSE 2
    END as education_level,
    
    -- Test graduation year parsing
    TRY(CAST(json_extract_scalar(json_parse(education), '$[0].end_date') AS INT)) as graduation_year,
    
    -- Test work experience count
    CASE 
        WHEN work_experience IS NOT NULL AND work_experience != '' AND work_experience != '[]' THEN
            TRY(CAST(json_array_length(json_parse(work_experience)) AS INT))
        ELSE NULL
    END as number_of_jobs,
    
    -- Test skill count
    CASE 
        WHEN skills IS NOT NULL AND skills != '' AND skills != '[]' THEN
            TRY(CAST(json_array_length(json_parse(skills)) AS INT))
        ELSE NULL
    END as skill_count,
    
    -- Show age for validation
    CASE 
        WHEN birth_year IS NOT NULL THEN 2025 - CAST(birth_year AS INT)
        ELSE CAST(approximate_age AS INT)
    END as actual_age,
    
    -- Show raw fields for debugging
    education,
    work_experience,
    skills

FROM ${SOURCE_DATABASE}.${SOURCE_TABLE}
WHERE pid IS NOT NULL
  AND education IS NOT NULL
  AND birth_year IS NOT NULL
LIMIT 10;

