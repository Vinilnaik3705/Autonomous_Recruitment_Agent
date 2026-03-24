import os
import psycopg2
from psycopg2.extras import RealDictCursor
import toml
from typing import Generator, Optional

def get_db_config():
    """Load database config from environment variables (priority) or secrets.toml."""
    # 1. DATABASE_URL (Docker / Production priority)
    if os.getenv("DATABASE_URL"):
        return {"dsn": os.getenv("DATABASE_URL")}

    config = {}
    # 2. Load secrets.toml if available (Local Dev)
    if os.path.exists("secrets.toml"):
        try:
            secrets = toml.load("secrets.toml")
            config = secrets.get('database', {})
        except Exception as e:
            print(f"Warning: Could not load secrets.toml: {e}")
    elif os.path.exists("../secrets.toml"):
        try:
            secrets = toml.load("../secrets.toml")
            config = secrets.get('database', {})
        except Exception as e:
            print(f"Warning: Could not load ../secrets.toml: {e}")
    
    # 3. Return Dictionary (Env vars override config file if needed, or fallback)
    return {
        'host': os.getenv('DB_HOST', config.get('host', 'localhost')),
        'database': os.getenv('DB_NAME', config.get('name', 'hr_db')),
        'user': os.getenv('DB_USER', config.get('user', 'hr_user')),
        'password': os.getenv('DB_PASSWORD', config.get('password', 'hr_pass')),
        'port': os.getenv('DB_PORT', config.get('port', 5433))
    }

def get_db_connection():
    """Create a new database connection to PostgreSQL."""
    config = get_db_config()

    def _display_target(db_config):
        if db_config.get("dsn"):
            return "DATABASE_URL DSN"
        return f"{db_config.get('host')}:{db_config.get('port')} (DB: {db_config.get('database')})"

    attempts = [("primary", dict(config))]

    if "dsn" not in config:
        host = str(config.get("host", "")).strip().lower()
        port = str(config.get("port", "5432"))
        enable_port_fallback = os.getenv("DB_ENABLE_PORT_FALLBACK", "false").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        if host == "postgres":
            localhost_config = dict(config)
            localhost_config["host"] = "localhost"
            attempts.append(("host fallback postgres->localhost", localhost_config))

        if enable_port_fallback:
            if port == "5433":
                port_fallback_config = dict(config)
                port_fallback_config["port"] = 5432
                attempts.append(("port fallback 5433->5432", port_fallback_config))

                if host == "postgres":
                    combined_fallback = dict(config)
                    combined_fallback["host"] = "localhost"
                    combined_fallback["port"] = 5432
                    attempts.append(("host+port fallback", combined_fallback))
            elif port == "5432":
                # In this project, Docker Postgres is commonly published as 5433 on host.
                port_fallback_config = dict(config)
                port_fallback_config["port"] = 5433
                attempts.append(("port fallback 5432->5433", port_fallback_config))

    last_error = None
    for label, attempt in attempts:
        try:
            if "port" in attempt:
                attempt["port"] = int(attempt.get("port", 5432))
            print(f"--> DB CONNECT: Attempt ({label}) -> {_display_target(attempt)}")
            conn = psycopg2.connect(**attempt)
            print("--> DB CONNECT: Success!")
            return conn
        except psycopg2.OperationalError as e:
            last_error = e
            print(f"--> DB CONNECT: Attempt failed ({label}): {e}")

    print(f"Database connection failed after {len(attempts)} attempt(s): {last_error}")
    raise last_error

def get_db_cursor() -> Generator:
    """Context manager for database cursor."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def close_db(db):
    """Close database connection."""
    if db:
        db.close()
