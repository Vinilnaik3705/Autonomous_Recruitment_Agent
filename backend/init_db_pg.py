"""
Initialize PostgreSQL database with RBAC schema and demo users.
"""
import hashlib
import os
from backend.database import get_db_connection

def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initialize database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create users table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'recruiter',
                workspace_id INTEGER,
                department VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("✓ Users table created")
        
    except Exception as e:
        print(f"Schema creation: {str(e)[:100]}")
        conn.rollback()
    
    conn.close()

def create_demo_users():
    """Create demo users for testing."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    demo_users = [
        ("admin", "admin@example.com", "password", "super_admin"),
        ("recruiter", "recruiter@example.com", "password", "recruiter"),
        ("interviewer", "interviewer@example.com", "password", "interviewer"),
        ("john.smith", "john.smith@company.com", "password", "recruiter"),
    ]
    
    for username, email, password, role in demo_users:
        hashed_pwd = hash_password(password)
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (username, email, hashed_pwd, role))
            conn.commit()
            print(f"  ✓ Created user: {email}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"  - User {email} already exists")
            else:
                print(f"  ✗ Error creating {email}: {str(e)[:50]}")
            conn.rollback()
    
    conn.close()

def main():
    """Initialize database and seed demo users."""
    print("Initializing PostgreSQL database...\n")
    
    try:
        init_db()
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        print("\nMake sure PostgreSQL is running on port 5433")
        print("See POSTGRESQL_SETUP.md for configuration instructions")
        return
    
    enable_demo_users = os.getenv("ENABLE_DEMO_USERS", "false").lower() in ("1", "true", "yes", "on")
    if enable_demo_users:
        print("\nCreating demo users...")
        create_demo_users()
    else:
        print("\nSkipping demo users (set ENABLE_DEMO_USERS=true to enable).")
    
    print("\n✓ Database initialization complete!")
    if enable_demo_users:
        print("\nDemo Credentials for Testing:")
        print("  Admin:        admin@example.com / password")
        print("  Recruiter:    recruiter@example.com / password")
        print("  Interviewer:  interviewer@example.com / password")
        print("  User:         john.smith@company.com / password")

if __name__ == "__main__":
    main()
