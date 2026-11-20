CREATE INDEX ON applications(job_id, status);
CREATE INDEX ON applications(candidate_user_id);
CREATE INDEX ON interviews(scheduled_start);
CREATE INDEX ON interviews(feedback_last_reminder_at) WHERE feedback_submitted_at IS NULL;
CREATE INDEX ON onboarding_tasks(status, due_date);
CREATE INDEX ON agent_runs(application_id, started_at);
CREATE INDEX ON applications USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON jobs USING hnsw (embedding vector_cosine_ops);
