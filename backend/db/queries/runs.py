from psycopg.types.json import Jsonb


def enqueue(conn, application_id, action, key, details=None, due=None):
    return conn.execute(
        """INSERT INTO agent_runs(application_id,agent_name,action,status,idempotency_key,details)
           VALUES (%s,'recruitment',%s,'running',%s,%s)
           ON CONFLICT (idempotency_key) DO NOTHING RETURNING id""",
        (
            application_id,
            action,
            key,
            Jsonb(
                {
                    **(details or {}),
                    "delivery": "queued",
                    "due_at": due.isoformat() if due else None,
                }
            ),
        ),
    ).fetchone()


def due(conn):
    return conn.execute(
        """SELECT id,action FROM agent_runs WHERE status='running' AND details->>'delivery'='queued'
           AND COALESCE((details->>'due_at')::timestamptz,now())<=now()
           ORDER BY started_at,id LIMIT 100"""
    ).fetchall()


def lock(conn, run_id):
    return conn.execute(
        "SELECT * FROM agent_runs WHERE id=%s FOR UPDATE SKIP LOCKED", (run_id,)
    ).fetchone()


def update(conn, run_id, status, delivery, **details):
    conn.execute(
        """UPDATE agent_runs SET status=%s,details=details || %s,
           finished_at=CASE WHEN %s='running' THEN NULL ELSE now() END WHERE id=%s""",
        (status, Jsonb({"delivery": delivery, **details}), status, run_id),
    )


def expire_dispatches(conn):
    conn.execute("""UPDATE agent_runs SET status='failed',finished_at=now(),
           details=jsonb_set(details,'{delivery}','"uncertain"')
           WHERE status='running' AND details->>'delivery'='sending'
           AND (details->>'claimed_at')::timestamptz < now() - interval '15 minutes'""")


def retry_screening(conn, application_id):
    return conn.execute(
        """UPDATE agent_runs SET status='running',finished_at=NULL,
                   details=jsonb_set(details,'{delivery}','"queued"')
           WHERE application_id=%s AND action='screen' AND status='failed'
           RETURNING id""",
        (application_id,),
    ).fetchone()


def record_transition(conn, application_id, previous, target):
    conn.execute(
        """INSERT INTO agent_runs(application_id,agent_name,action,from_status,to_status,status,finished_at)
           VALUES (%s,'workflow','transition',%s,%s,'success',now())""",
        (application_id, previous, target),
    )


def pending_for(conn, application_id):
    return conn.execute(
        """SELECT 1 FROM agent_runs WHERE application_id=%s AND action IN ('book','reschedule','offer')
           AND details->>'delivery' IN ('queued','sending','uncertain') LIMIT 1""",
        (application_id,),
    ).fetchone()


def activity(conn, application_id):
    return conn.execute(
        """SELECT id,action,from_status,to_status,status,started_at,finished_at,
                  details->>'delivery' AS delivery
           FROM agent_runs WHERE application_id=%s ORDER BY id DESC LIMIT 100""",
        (application_id,),
    ).fetchall()
