import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import Generator, Optional

load_dotenv()

def get_db_config():
    """Load database config from environment variables (.env file)."""

    if os.getenv("DATABASE_URL"):
        return {"dsn": os.getenv("DATABASE_URL")}

    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'hr_db'),
        'user': os.getenv('DB_USER', 'hr_user'),
        'password': os.getenv('DB_PASSWORD', 'hr_pass'),
        'port': os.getenv('DB_PORT', 5433)
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

import redis

_redis_client = None

def get_redis_client():
    """Retrieve or initialize a Redis client. Returns None if connection fails (resilient fallback)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:

        client = redis.from_url(redis_url, socket_connect_timeout=2.0, socket_timeout=2.0)
        client.ping()
        _redis_client = client
        print(f"--> REDIS CONNECT: Success ({redis_url})")
        return _redis_client
    except Exception as e:
        print(f"--> REDIS CONNECT: Failed ({redis_url}): {e}. Caching is disabled.")
        return None

import json

def cache_get(key: str):
    """Get JSON-deserialized value from Redis."""
    client = get_redis_client()
    if client:
        try:
            val = client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            print(f"--> REDIS CACHE GET ERROR: {e}")
    return None

def cache_set(key: str, value, ttl: int = 10):
    """Set JSON-serialized value in Redis with a TTL (seconds)."""
    client = get_redis_client()
    if client:
        try:
            client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            print(f"--> REDIS CACHE SET ERROR: {e}")

def cache_delete(key: str):
    """Delete a key from Redis cache."""
    client = get_redis_client()
    if client:
        try:
            client.delete(key)
        except Exception as e:
            print(f"--> REDIS CACHE DELETE ERROR: {e}")