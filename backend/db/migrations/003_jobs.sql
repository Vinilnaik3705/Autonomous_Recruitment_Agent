CREATE TABLE jobs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title text NOT NULL,
    description text NOT NULL,
    required_skills text[] NOT NULL DEFAULT '{}',
    min_experience_years numeric CHECK (min_experience_years >= 0),
    location text,
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','open','closed')),
    embedding vector(384),
    created_by bigint NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now()
);
