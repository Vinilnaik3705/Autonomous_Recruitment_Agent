import os
import psycopg2
from psycopg2.extras import RealDictCursor
import toml
from typing import Generator, Optional

def get_db_config():
    """Load database config from environment variables (priority) or secrets.toml."""
    config = {}
    
    # Load secrets.toml if available
    if os.path.exists("secrets.toml"):
        try:
            secrets = toml.load("secrets.toml")
            config = secrets.get('database', {})
        except Exception: pass
    elif os.path.exists("../secrets.toml"):
        try:
            secrets = toml.load("../secrets.toml")
            config = secrets.get('database', {})
        except Exception: pass

    # Get values from env or config
    host = os.getenv('DB_HOST', config.get('host', 'localhost'))
    database = os.getenv('DB_NAME', config.get('name', 'hr_db'))
    user = os.getenv('DB_USER', config.get('user', 'hr_user'))
    password = os.getenv('DB_PASSWORD', config.get('password', 'hr_pass'))
    port = os.getenv('DB_PORT', config.get('port', 5433))

    # Also handle DATABASE_URL if present, but extract components for better fallback
    db_url = os.getenv("DATABASE_URL")
    if db_url and "postgres" in db_url:
        # Simple extraction if possible, else use as is
        print(f"--> DB CONFIG: DATABASE_URL detected.")
        return {"dsn": db_url}

    return {
        'host': host,
        'database': database,
        'user': user,
        'password': password,
        'port': port
    }

# Simple global cache to remember what worked
_worked_config: Optional[dict] = None

def get_db_connection():
    """Create a new database connection with smart host/port fallback."""
    global _worked_config
    
    if _worked_config:
        try:
            return psycopg2.connect(**_worked_config, connect_timeout=1)
        except Exception:
            _worked_config = None # Reset cache if it fails

    base_config = get_db_config()
    
    # If using DSN, we have limited fallback unless we parse it.
    if "dsn" in base_config:
        try:
            conn = psycopg2.connect(dsn=base_config["dsn"], connect_timeout=2)
            _worked_config = {"dsn": base_config["dsn"]}
            return conn
        except Exception as e:
            print(f"--> DB CONNECT: DSN failed: {e}. Trying localhost fallbacks...")

    # Aggressive fallback list for local dev
    hosts = ['127.0.0.1', 'localhost', 'postgres']
    ports = [5433, 5432]
    
    # Prioritize values from config
    prio_host = base_config.get('host')
    prio_port = int(base_config.get('port', 5433))
    
    if prio_host in hosts: hosts.remove(prio_host)
    hosts.insert(0, prio_host)
    if prio_port in ports: ports.remove(prio_port)
    ports.insert(0, prio_port)

    for host in hosts:
        for port in ports:
            try:
                test_config = {
                    'host': host,
                    'port': port,
                    'database': base_config.get('database', 'hr_db'),
                    'user': base_config.get('user', 'hr_user'),
                    'password': base_config.get('password', 'hr_pass'),
                    'connect_timeout': 1
                }
                conn = psycopg2.connect(**test_config)
                print(f"--> DB CONNECT: Success on {host}:{port}!")
                # Remove timeout from cached config for actual usage if desired, 
                # but connect_timeout=1 is usually fine.
                _worked_config = test_config
                return conn
            except Exception:
                continue
            
    raise Exception("Database connection failed. Tried multiple hosts/ports. Is PostgreSQL running?")

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
    """Safely close database connection."""
    if db is not None:
        try:
            db.close()
        except Exception as e:
            print(f"Warning: Error closing database connection: {e}")
