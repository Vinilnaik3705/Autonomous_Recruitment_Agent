CREATE TABLE users (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email text NOT NULL UNIQUE CHECK (email = lower(trim(email))),
    password_hash text NOT NULL,
    full_name text NOT NULL,
    role text NOT NULL DEFAULT 'candidate' CHECK (role IN ('admin','hr','interviewer','candidate')),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    expertise text[],
    timezone text,
    calendar_id text,
    availability jsonb,
    google_refresh_token_encrypted text
);
