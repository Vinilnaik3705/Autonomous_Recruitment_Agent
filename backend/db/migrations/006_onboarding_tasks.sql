CREATE TABLE onboarding_tasks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    application_id bigint NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    task_type text NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','submitted','verified')),
    due_date date,
    file_path text,
    reminder_count integer NOT NULL DEFAULT 0 CHECK (reminder_count >= 0),
    last_reminder_at timestamptz,
    escalated_to_hr boolean NOT NULL DEFAULT false,
    UNIQUE(application_id, task_type)
);
