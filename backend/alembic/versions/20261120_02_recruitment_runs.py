"""Durable candidate workflow and outbound action log."""

from alembic import op

revision = "20261120_02"
down_revision = "20261120_01"
branch_labels = depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE agent_runs (
            id serial PRIMARY KEY, owner_id integer NOT NULL, request_key uuid NOT NULL, candidate_user_id integer, claim_hash text UNIQUE, email text NOT NULL,
            filename text NOT NULL, document bytea, job_description text NOT NULL,
            required_skills text[] NOT NULL, stage text NOT NULL DEFAULT 'applied',
            screening_state text NOT NULL DEFAULT 'queued', result jsonb,
            feedback text, interview_at timestamptz, offer text, approved_by integer,
            checklist text[], completion_note text, embedding vector(384), UNIQUE(owner_id, request_key), created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE TABLE recruitment_actions (
            id serial PRIMARY KEY, run_id integer NOT NULL REFERENCES agent_runs(id),
            kind text NOT NULL, body jsonb NOT NULL, state text NOT NULL DEFAULT 'pending',
            available_at timestamptz NOT NULL DEFAULT now(), claimed_at timestamptz,
            provider_id text, UNIQUE(run_id, kind, available_at)
        );
        CREATE INDEX recruitment_actions_due ON recruitment_actions(available_at)
            WHERE state = 'pending'
    """)


def downgrade():
    op.drop_table("recruitment_actions")
    op.drop_table("agent_runs")
