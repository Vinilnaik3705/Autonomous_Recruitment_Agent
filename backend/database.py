import os
import psycopg2
from psycopg2.extras import RealDictCursor
import toml
from typing import Generator, Optional

def get_db_config():
    """Load database config from secrets.toml or environment variables."""
    config = {}
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
    
    return {
        'host': config.get('host', os.getenv('DB_HOST', 'localhost')),
        'database': config.get('name', os.getenv('DB_NAME', 'resume_analyzer')),
        'user': config.get('user', os.getenv('DB_USER', 'postgres')),
        'password': config.get('password', os.getenv('DB_PASSWORD', 'password')),
        'port': config.get('port', os.getenv('DB_PORT', '5432'))
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
