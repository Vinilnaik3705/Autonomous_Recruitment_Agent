-- Add missing columns to interview_schedules table
ALTER TABLE interview_schedules ADD COLUMN IF NOT EXISTS reminder_24h_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE interview_schedules ADD COLUMN IF NOT EXISTS round_number INTEGER;
ALTER TABLE interview_schedules ADD COLUMN IF NOT EXISTS round_label VARCHAR(255);

-- Add missing columns to resume_data table
ALTER TABLE resume_data ADD COLUMN IF NOT EXISTS email_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE resume_data ADD COLUMN IF NOT EXISTS sample_oa_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE resume_data ADD COLUMN IF NOT EXISTS sample_oa_sent_at TIMESTAMP;
ALTER TABLE resume_data ADD COLUMN IF NOT EXISTS official_oa_sent BOOLEAN DEFAULT FALSE;
ALTER TABLE resume_data ADD COLUMN IF NOT EXISTS official_oa_sent_at TIMESTAMP;
