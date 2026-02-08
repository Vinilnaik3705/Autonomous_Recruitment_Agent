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
        'database': os.getenv('DB_NAME', config.get('name', 'resume_analyzer')),
        'user': os.getenv('DB_USER', config.get('user', 'postgres')),
        'password': os.getenv('DB_PASSWORD', config.get('password', 'password')),
        'port': os.getenv('DB_PORT', config.get('port', '5432'))
    }

def get_db_connection():
    """Create a new database connection."""
    config = get_db_config()
    try:
        conn = psycopg2.connect(**config)
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise e

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
