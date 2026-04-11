-- Speed up screening result polling and duplicate checks.
CREATE INDEX IF NOT EXISTS idx_resume_data_job_score_created
ON resume_data(job_id, ai_score DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_resume_data_job_email_lower
ON resume_data(job_id, LOWER(email));

-- Helps scheduled-interview dedupe checks in batch screening.
CREATE INDEX IF NOT EXISTS idx_interview_schedules_status_candidate_email
ON interview_schedules(status, candidate_email);
