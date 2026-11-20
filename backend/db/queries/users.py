def create(conn, email, full_name, password_hash):
    return conn.execute(
        """INSERT INTO users(email, full_name, password_hash) VALUES (%s,%s,%s)
           ON CONFLICT (email) DO NOTHING RETURNING id, email, full_name, role""",
        (email, full_name, password_hash),
    ).fetchone()


def by_email(conn, email):
    return conn.execute("SELECT * FROM users WHERE email=%s", (email,)).fetchone()


def by_id(conn, user_id):
    return conn.execute(
        "SELECT id,email,full_name,role,is_active FROM users WHERE id=%s", (user_id,)
    ).fetchone()


def interviewers(conn):
    return conn.execute(
        "SELECT id,full_name FROM users WHERE role='interviewer' AND is_active ORDER BY full_name,id"
    ).fetchall()


def create_staff(conn, email, full_name, password_hash, role):
    return conn.execute(
        """INSERT INTO users(email,full_name,password_hash,role) VALUES (%s,%s,%s,%s)
           ON CONFLICT (email) DO NOTHING RETURNING id""",
        (email, full_name, password_hash, role),
    ).fetchone()
