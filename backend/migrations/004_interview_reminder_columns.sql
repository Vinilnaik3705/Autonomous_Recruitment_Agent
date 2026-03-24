-- Migration: Interview reminder tracking columns
-- Ensures reminder workflow queries in n8n run on existing databases.

ALTER TABLE interview_schedules
    ADD COLUMN IF NOT EXISTS round_number INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS round_label VARCHAR(100) DEFAULT 'Interview',
    ADD COLUMN IF NOT EXISTS interview_format VARCHAR(50) DEFAULT 'video call',
    ADD COLUMN IF NOT EXISTS reminder_24h_sent BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reminder_1h_sent BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reminder_24h_sent_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS reminder_1h_sent_at TIMESTAMP;

UPDATE interview_schedules
SET reminder_24h_sent = FALSE
WHERE reminder_24h_sent IS NULL;

UPDATE interview_schedules
SET reminder_1h_sent = FALSE
WHERE reminder_1h_sent IS NULL;

CREATE INDEX IF NOT EXISTS idx_interview_schedules_reminder_window
    ON interview_schedules(status, scheduled_time)
    WHERE status = 'scheduled';

DO $$
BEGIN
    RAISE NOTICE 'Migration completed: interview reminder columns are ready.';
END $$;
