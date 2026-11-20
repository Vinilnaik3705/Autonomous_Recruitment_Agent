import numpy as np
from psycopg.types.json import Jsonb


def create(conn, job_id, full_name, email, candidate_id, resume_path):
    return conn.execute(
        """INSERT INTO applications(job_id,full_name,email,candidate_user_id,resume_path)
           SELECT id,%s,%s,%s,%s FROM jobs WHERE id=%s AND status='open'
           ON CONFLICT (job_id,email) DO NOTHING RETURNING id,job_id,status""",
        (full_name, email, candidate_id, resume_path, job_id),
    ).fetchone()


def list_for(conn, candidate_id=None):
    return conn.execute(
        """SELECT a.id,a.job_id,j.title,a.full_name,a.email,a.status,a.applied_at,a.match_score,
                  a.score_breakdown,a.parsed_data,a.parsed_at
           FROM applications a JOIN jobs j ON j.id=a.job_id
           WHERE a.deleted_at IS NULL AND (%s::bigint IS NULL OR a.candidate_user_id=%s)
           ORDER BY a.id DESC LIMIT 100""",
        (candidate_id, candidate_id),
    ).fetchall()


def screening_input(conn, application_id):
    return conn.execute(
        """SELECT a.resume_path,j.description,j.embedding AS job_embedding,j.required_skills
           FROM applications a JOIN jobs j ON j.id=a.job_id
           WHERE a.id=%s AND a.status='applied' AND a.deleted_at IS NULL FOR UPDATE OF a SKIP LOCKED""",
        (application_id,),
    ).fetchone()


def save_screening(conn, application_id, data, score):
    conn.execute(
        """UPDATE applications SET status='screened', parsed_data=%s,resume_text=%s,
             embedding=%s,parsed_at=now(),updated_at=now(),match_score=%s,score_breakdown=%s
           WHERE id=%s""",
        (
            Jsonb(data["fields"]),
            data["text"],
            np.asarray(data["embedding"], dtype=np.float32),
            score.combined_score,
            Jsonb(score.model_dump()),
            application_id,
        ),
    )


def similar(conn, job_id, embedding, limit):
    return conn.execute(
        """SELECT id,full_name, status, 1-(embedding <=> %s) AS similarity
           FROM applications WHERE job_id=%s AND deleted_at IS NULL AND embedding IS NOT NULL
           ORDER BY embedding <=> %s LIMIT %s""",
        (embedding, job_id, embedding, limit),
    ).fetchall()


def lock(conn, application_id):
    return conn.execute(
        """SELECT id,email,status,full_name FROM applications
           WHERE id=%s AND deleted_at IS NULL FOR UPDATE""",
        (application_id,),
    ).fetchone()


def set_status(conn, application_id, status, approver=None):
    conn.execute(
        """UPDATE applications SET status=%s,updated_at=now(),
           shortlisted=(shortlisted OR %s='shortlisted'),
           approved_by=COALESCE(%s,approved_by),
           approved_at=CASE WHEN %s::bigint IS NULL THEN approved_at ELSE now() END,
           offer_status=CASE WHEN %s='onboarding' THEN 'accepted' ELSE offer_status END
           WHERE id=%s""",
        (status, status, approver, approver, status, application_id),
    )


def claim(conn, application_id, identity, token_hash):
    return conn.execute(
        """UPDATE applications a SET candidate_user_id=%s,updated_at=now()
           WHERE a.id=%s AND a.email=%s AND a.candidate_user_id IS NULL AND a.deleted_at IS NULL
           AND EXISTS (SELECT 1 FROM agent_runs r WHERE r.application_id=a.id
                       AND r.action='invite' AND r.details->>'claim_hash'=%s)
           RETURNING a.id""",
        (identity["id"], application_id, identity["email"], token_hash),
    ).fetchone()


def offer_sent(conn, application_id):
    conn.execute(
        """UPDATE applications SET status='offer_sent',offer_status='sent',offer_sent_at=now(),
             pending_approval=NULL,updated_at=now() WHERE id=%s""",
        (application_id,),
    )


def approve_offer(conn, application_id, user_id):
    conn.execute(
        """UPDATE applications SET pending_approval='offer',offer_status='draft',
           approved_by=%s,approved_at=now(),updated_at=now() WHERE id=%s""",
        (user_id, application_id),
    )


def owned_by(conn, application_id, candidate_id):
    return conn.execute(
        "SELECT 1 FROM applications WHERE id=%s AND candidate_user_id=%s AND deleted_at IS NULL",
        (application_id, candidate_id),
    ).fetchone()
