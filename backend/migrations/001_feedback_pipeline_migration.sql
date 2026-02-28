-- Migration for Feedback Collection & Decision Pipeline
-- This migration adds necessary columns and updates the schema to support
-- the complete autonomous feedback collection workflow

-- Add missing columns to interview_schedules table
ALTER TABLE interview_schedules 
    ADD COLUMN IF NOT EXISTS job_title VARCHAR(255),
    ADD COLUMN IF NOT EXISTS interviewer_name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS interviewer_email VARCHAR(100),
    ADD COLUMN IF NOT EXISTS feedback_requested_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS resume_id INTEGER;

-- Update interview_feedback table to match workflow expectations
ALTER TABLE interview_feedback
    ADD COLUMN IF NOT EXISTS technical_score INTEGER,
    ADD COLUMN IF NOT EXISTS communication_score INTEGER,
    ADD COLUMN IF NOT EXISTS cultural_fit_score INTEGER,
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create index for faster interview lookup
CREATE INDEX IF NOT EXISTS idx_interview_schedules_status 
    ON interview_schedules(status);

CREATE INDEX IF NOT EXISTS idx_interview_schedules_time 
    ON interview_schedules(scheduled_time);

-- Add final_decision column to resume_data for tracking hiring outcomes
ALTER TABLE resume_data
    ADD COLUMN IF NOT EXISTS final_decision VARCHAR(50),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Update existing interview status values to match new workflow
UPDATE interview_schedules 
SET status = 'scheduled' 
WHERE status IN ('pending', 'confirmed');

-- Create a view for easy feedback analytics
CREATE OR REPLACE VIEW feedback_analytics AS
SELECT 
    i.id as interview_id,
    i.candidate_name,
    i.candidate_email,
    i.job_title,
    i.scheduled_time,
    i.status,
    inv.name as interviewer_name,
    inv.email as interviewer_email,
    f.technical_score,
    f.communication_score,
    f.cultural_fit_score,
    f.overall_rating,
    f.recommendation,
    f.comments,
    f.submitted_at,
    CASE 
        WHEN f.recommendation = 'ACCEPT' THEN 'Selected'
        WHEN f.recommendation = 'REJECT' THEN 'Rejected'
        WHEN f.recommendation = 'ON_HOLD' THEN 'Pending Review'
        ELSE 'No Feedback'
    END as decision_status,
    ROUND((f.technical_score + f.communication_score + f.cultural_fit_score) / 3.0, 2) as avg_score
FROM interview_schedules i
LEFT JOIN interviewers inv ON i.interviewer_id = inv.id
LEFT JOIN interview_feedback f ON i.id = f.interview_id
ORDER BY i.scheduled_time DESC;

-- Insert sample interviewer data (if needed for testing)
INSERT INTO interviewers (name, email, timezone, is_active)
VALUES 
    ('John Smith', 'john.smith@company.com', 'America/New_York', TRUE),
    ('Sarah Johnson', 'sarah.johnson@company.com', 'America/Los_Angeles', TRUE),
    ('Michael Chen', 'michael.chen@company.com', 'Asia/Singapore', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_interview_schedules_updated_at ON interview_schedules;
CREATE TRIGGER update_interview_schedules_updated_at 
    BEFORE UPDATE ON interview_schedules 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_resume_data_updated_at ON resume_data;
CREATE TRIGGER update_resume_data_updated_at 
    BEFORE UPDATE ON resume_data 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Feedback collection pipeline schema is now ready.';
END $$;
