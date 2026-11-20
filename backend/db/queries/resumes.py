"""Keep uploads in the same transaction and database as the application."""


def store(conn, content, suffix):
    row = conn.execute("SELECT lo_from_bytea(0, %s) AS oid", (content,)).fetchone()
    return f"{row['oid']}{suffix}"


def read(conn, path):
    oid = int(path.split(".", 1)[0])
    return conn.execute("SELECT lo_get(%s::oid) AS data", (oid,)).fetchone()["data"]
