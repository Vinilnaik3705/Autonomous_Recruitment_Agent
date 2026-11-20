CREATE TABLE agent_runs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    application_id bigint NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    agent_name text NOT NULL,
    action text NOT NULL,
    from_status text CHECK (from_status IN ('applied','screened','shortlisted','interview_scheduled','interviewed',
       'feedback_received','selected','rejected','hold','offer_sent','onboarding','complete')),
    to_status text CHECK (to_status IN ('applied','screened','shortlisted','interview_scheduled','interviewed',
       'feedback_received','selected','rejected','hold','offer_sent','onboarding','complete')),
    status text NOT NULL CHECK (status IN ('running','success','failed')),
    idempotency_key text UNIQUE,
    details jsonb NOT NULL DEFAULT '{}',
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz
);
