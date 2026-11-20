def create(conn, application_id, task_type, due_date):
    conn.execute(
        "INSERT INTO onboarding_tasks(application_id,task_type,due_date) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
        (application_id, task_type, due_date),
    )


def update(conn, application_id, task_id, old_status, status):
    return conn.execute(
        """UPDATE onboarding_tasks SET status=%s WHERE id=%s AND application_id=%s
           AND status=%s RETURNING id""",
        (status, task_id, application_id, old_status),
    ).fetchone()


def list_for(conn, application_id):
    return conn.execute(
        """SELECT id,task_type,status,due_date FROM onboarding_tasks
           WHERE application_id=%s ORDER BY id""",
        (application_id,),
    ).fetchall()
