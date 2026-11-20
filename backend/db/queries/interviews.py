def get(conn, application_id):
    return conn.execute(
        "SELECT * FROM interviews WHERE application_id=%s AND round_number=1",
        (application_id,),
    ).fetchone()


def save(conn, application_id, interviewer_id, start, end, event_id):
    return conn.execute(
        """INSERT INTO interviews(application_id,interviewer_id,round_number,scheduled_start,scheduled_end,google_event_id)
           VALUES (%s,%s,1,%s,%s,%s)
           ON CONFLICT(application_id,round_number) DO UPDATE SET
             scheduled_start=excluded.scheduled_start,scheduled_end=excluded.scheduled_end,
             interviewer_id=excluded.interviewer_id,google_event_id=excluded.google_event_id,
             reschedule_count=interviews.reschedule_count+1,status='rescheduled',reminder_sent_at=NULL
           RETURNING id""",
        (application_id, interviewer_id, start, end, event_id),
    ).fetchone()


def feedback(conn, application_id, comments, score, recommendation):
    return conn.execute(
        """UPDATE interviews SET feedback_submitted_at=now(),feedback_comments=%s,
           feedback_scores=%s,recommendation=%s,status='completed'
           WHERE application_id=%s AND round_number=1 AND feedback_submitted_at IS NULL
           RETURNING id""",
        (comments, score, recommendation, application_id),
    ).fetchone()


def mark_reminded(conn, application_id):
    conn.execute(
        "UPDATE interviews SET reminder_sent_at=now() WHERE application_id=%s AND round_number=1",
        (application_id,),
    )


def assigned(conn, user_id):
    return conn.execute(
        """SELECT i.id,i.application_id,i.scheduled_start,i.scheduled_end,i.status,
                  i.feedback_submitted_at,a.full_name,j.title
           FROM interviews i JOIN applications a ON a.id=i.application_id
           JOIN jobs j ON j.id=a.job_id
           WHERE i.interviewer_id=%s AND a.deleted_at IS NULL ORDER BY i.scheduled_start""",
        (user_id,),
    ).fetchall()


def reserve_calendar(conn, application_id, start, end):
    conn.execute("SELECT pg_advisory_xact_lock(%s)", (781291,))
    return conn.execute(
        """SELECT 1 FROM interviews
           WHERE application_id<>%s AND status IN ('scheduled','rescheduled')
             AND scheduled_start<%s AND scheduled_end>%s
           UNION ALL
           SELECT 1 FROM agent_runs
           WHERE application_id<>%s AND action IN ('book','reschedule')
             AND details->>'delivery' IN ('queued','sending','uncertain')
             AND (details->>'start')::timestamptz < %s
             AND (details->>'start')::timestamptz + interval '1 hour' > %s
           LIMIT 1""",
        (application_id, end, start, application_id, end, start),
    ).fetchone()
