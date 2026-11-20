"""Apply immutable SQL migrations in filename order."""

from pathlib import Path

import psycopg

from backend.config import get_settings


def migrate(database_url: str) -> list[str]:
    applied = []
    files = sorted(Path(__file__).with_name("migrations").glob("*.sql"))
    with psycopg.connect(database_url, autocommit=True) as conn:
        # Hold the lock across transactions so simultaneous starts cannot race.
        conn.execute("SELECT pg_advisory_lock(%s)", (782025,))
        for migration in files:
            with conn.transaction():
                if migration.name == "000_schema_migrations.sql":
                    conn.execute(migration.read_text())
                if conn.execute(
                    "SELECT 1 FROM schema_migrations WHERE filename = %s",
                    (migration.name,),
                ).fetchone():
                    continue
                if migration.name != "000_schema_migrations.sql":
                    conn.execute(migration.read_text())
                conn.execute(
                    "INSERT INTO schema_migrations(filename) VALUES (%s)",
                    (migration.name,),
                )
                applied.append(migration.name)
    return applied


if __name__ == "__main__":
    filenames = migrate(get_settings().database_url)
    print("\n".join(filenames) if filenames else "No pending migrations.")
