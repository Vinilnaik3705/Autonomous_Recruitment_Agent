-- Migration for OA Result Tracking & Immediate Score Updates
-- This migration ensures the resume_data table has all necessary OA tracking columns
-- for immediate score updates after exam completion

-- Add OA tracking columns to resume_data if they don't exist
ALTER TABLE resume_data
    ADD COLUMN IF NOT EXISTS oa_score DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS oa_status VARCHAR(50) DEFAULT 'uninvited',
    ADD COLUMN IF NOT EXISTS oa_report_url TEXT,
    ADD COLUMN IF NOT EXISTS official_oa_sent BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sample_oa_sent BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sample_oa_sent_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS oa_completed_at TIMESTAMP;

-- Create index for faster OA status lookups
CREATE INDEX IF NOT EXISTS idx_resume_data_oa_status 
    ON resume_data(oa_status);

CREATE INDEX IF NOT EXISTS idx_resume_data_oa_score 
    ON resume_data(oa_score);

CREATE INDEX IF NOT EXISTS idx_resume_data_email 
    ON resume_data(email);

-- Create a view for OA completion analytics
CREATE OR REPLACE VIEW oa_completion_analytics AS
SELECT 
    id,
    candidate_name,
    email,
    oa_score,
    oa_status,
    oa_completed_at,
    CASE WHEN oa_score >= 60 THEN 'PASSED' ELSE 'FAILED' END as oa_result,
    EXTRACT(EPOCH FROM (oa_completed_at - created_at)) / 3600 as hours_to_complete
FROM resume_data
WHERE oa_status = 'completed';

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_resume_data_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_resume_data_timestamp ON resume_data;
CREATE TRIGGER update_resume_data_timestamp
BEFORE UPDATE ON resume_data
FOR EACH ROW
EXECUTE FUNCTION update_resume_data_timestamp();
