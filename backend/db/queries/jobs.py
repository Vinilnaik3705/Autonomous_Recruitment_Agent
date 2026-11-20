import numpy as np


def create(conn, job, user_id, embedding):
    return conn.execute(
        """INSERT INTO jobs(title,description,required_skills,min_experience_years,location,status,created_by,embedding)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
           RETURNING id,title,description,required_skills,min_experience_years,location,status,created_by,created_at""",
        (
            job.title,
            job.description,
            job.required_skills,
            job.min_experience_years,
            job.location,
            job.status,
            user_id,
            np.asarray(embedding, dtype=np.float32),
        ),
    ).fetchone()


def list_open(conn):
    return conn.execute(
        "SELECT id,title,description,required_skills,location,status FROM jobs WHERE status='open' ORDER BY id DESC"
    ).fetchall()


def embedding_for(conn, job_id):
    return conn.execute("SELECT embedding FROM jobs WHERE id=%s", (job_id,)).fetchone()
