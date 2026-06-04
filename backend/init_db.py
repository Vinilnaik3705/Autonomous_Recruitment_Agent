import os
from pathlib import Path
from backend.database import get_db_connection

def _run_sql_migrations(cur):
    """Apply SQL files in backend/migrations once, tracked in schema_migrations."""
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    if not migrations_dir.exists():
        return

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    for migration_file in sorted(migrations_dir.glob("*.sql")):
        migration_name = migration_file.name
        cur.execute(
            "SELECT 1 FROM schema_migrations WHERE filename = %s",
            (migration_name,),
        )
        if cur.fetchone():
            continue

        sql_text = migration_file.read_text(encoding="utf-8")
        savepoint_name = f"mig_{migration_name.replace('.', '_').replace('-', '_')}"
        cur.execute(f"SAVEPOINT {savepoint_name}")
        try:
            cur.execute(sql_text)
            cur.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (migration_name,),
            )
            print(f"Applied migration: {migration_name}")
        except Exception as migration_error:

            cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            print(f"Skipping migration {migration_name}: {migration_error}")
        finally:
            cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")

def _apply_schema_hotfixes(cur):
    """Patch legacy schemas used by existing n8n workflows without destructive changes."""
    cur.execute(
        """
        ALTER TABLE resume_data
            ADD COLUMN IF NOT EXISTS email_sent BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS official_oa_sent BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS sample_oa_sent BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS sample_oa_sent_at TIMESTAMP,
            ADD COLUMN IF NOT EXISTS oa_score DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS oa_status VARCHAR(50) DEFAULT 'uninvited',
            ADD COLUMN IF NOT EXISTS oa_report_url TEXT,
            ADD COLUMN IF NOT EXISTS oa_completed_at TIMESTAMP,
            ADD COLUMN IF NOT EXISTS final_decision VARCHAR(50),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ADD COLUMN IF NOT EXISTS organization_id VARCHAR(100)
        """
    )

    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_id VARCHAR(100)")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT")
    cur.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS user_id INTEGER")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)"
    )
    cur.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS organization_id VARCHAR(100)")
    cur.execute("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS organization_id VARCHAR(100)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            action VARCHAR(255) NOT NULL,
            entity_type VARCHAR(100),
            entity_id VARCHAR(100),
            ip_address VARCHAR(45),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        UPDATE resume_data
        SET email_sent = FALSE
        WHERE email_sent IS NULL
        """
    )

    cur.execute(
        """
        UPDATE resume_data
        SET official_oa_sent = FALSE
        WHERE official_oa_sent IS NULL
        """
    )

    cur.execute(
        """
        UPDATE resume_data
        SET sample_oa_sent = FALSE
        WHERE sample_oa_sent IS NULL
        """
    )

    cur.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'unique_candidate_schedule'
            ) THEN
                ALTER TABLE interview_schedules
                    ADD CONSTRAINT unique_candidate_schedule
                    UNIQUE (candidate_email, scheduled_time);
            END IF;
        END $$;
        """
    )

    cur.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY LOWER(TRIM(candidate_email))
                    ORDER BY scheduled_time ASC NULLS LAST, created_at ASC
                ) AS rn
            FROM interview_schedules
            WHERE candidate_email IS NOT NULL
              AND TRIM(candidate_email) <> ''
              AND status IN ('scheduled', 'in_progress')
        )
        UPDATE interview_schedules s
        SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
        FROM ranked r
        WHERE s.id = r.id
          AND r.rn > 1
        """
    )

    cur.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_unique_active_interview_per_candidate'
            ) THEN
                CREATE UNIQUE INDEX idx_unique_active_interview_per_candidate
                ON interview_schedules ((LOWER(TRIM(candidate_email))))
                WHERE status IN ('scheduled', 'in_progress')
                  AND candidate_email IS NOT NULL
                  AND TRIM(candidate_email) <> '';
            END IF;
        EXCEPTION
            WHEN others THEN
                RAISE NOTICE 'Skipping idx_unique_active_interview_per_candidate: %', SQLERRM;
        END $$;
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_resume_data_sample_oa_window
        ON resume_data(sample_oa_sent, official_oa_sent, sample_oa_sent_at)
        """
    )

def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    role VARCHAR(20) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS job_descriptions (
                    job_id VARCHAR(50) PRIMARY KEY,
                    title VARCHAR(255),
                    description TEXT,
                    required_skills TEXT,
                    min_experience INT DEFAULT 0,
                    max_experience INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS interviewers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    calendar_id VARCHAR(100),
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    working_hours_start TIME DEFAULT '09:00',
                    working_hours_end TIME DEFAULT '17:00',
                    buffer_between_interviews_minutes INTEGER DEFAULT 15,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS resume_files (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    filename VARCHAR(255) NOT NULL,
                    file_size INTEGER,
                    file_type VARCHAR(20),
                    processed BOOLEAN DEFAULT FALSE,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id VARCHAR(50)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS resume_data (
                    id SERIAL PRIMARY KEY,
                    job_id VARCHAR(50),
                    candidate_name VARCHAR(255),
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    resume_url TEXT,
                    skills TEXT,
                    education TEXT,
                    ai_score FLOAT DEFAULT 0,
                    ai_summary TEXT,
                    interview_status VARCHAR(50) DEFAULT 'NEW',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(job_id, email)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    email TEXT UNIQUE,
                    phone TEXT,
                    file_name TEXT,
                    skills TEXT,
                    match_score FLOAT,
                    resume_shortlisted BOOLEAN DEFAULT FALSE,
                    oa_date TIMESTAMP,
                    oa_practice_sent BOOLEAN DEFAULT FALSE,
                    oa_original_sent BOOLEAN DEFAULT FALSE,
                    oa_score INTEGER,
                    reminder_2d_sent BOOLEAN DEFAULT FALSE,
                    reminder_1d_sent BOOLEAN DEFAULT FALSE,
                    reminder_1h_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS interview_schedules (
                    id SERIAL PRIMARY KEY,
                    candidate_name VARCHAR(100),
                    candidate_email VARCHAR(100),
                    interviewer_id INTEGER REFERENCES interviewers(id),
                    scheduled_time TIMESTAMP,
                    duration_minutes INTEGER DEFAULT 30,
                    meeting_link TEXT,
                    round_number INTEGER DEFAULT 1,
                    round_label VARCHAR(100) DEFAULT 'Interview',
                    interview_format VARCHAR(50) DEFAULT 'video call',
                    status VARCHAR(20) DEFAULT 'scheduled',
                    google_event_id VARCHAR(255),
                    reminder_24h_sent BOOLEAN DEFAULT FALSE,
                    reminder_1h_sent BOOLEAN DEFAULT FALSE,
                    reminder_24h_sent_at TIMESTAMP,
                    reminder_1h_sent_at TIMESTAMP,
                    feedback_submitted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                ALTER TABLE interview_schedules
                    ADD COLUMN IF NOT EXISTS round_number INTEGER DEFAULT 1,
                    ADD COLUMN IF NOT EXISTS round_label VARCHAR(100) DEFAULT 'Interview',
                    ADD COLUMN IF NOT EXISTS interview_format VARCHAR(50) DEFAULT 'video call',
                    ADD COLUMN IF NOT EXISTS reminder_24h_sent BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS reminder_1h_sent BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS reminder_24h_sent_at TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS reminder_1h_sent_at TIMESTAMP
            """)

            cur.execute("""
                UPDATE interview_schedules
                SET reminder_24h_sent = FALSE
                WHERE reminder_24h_sent IS NULL
            """)
            cur.execute("""
                UPDATE interview_schedules
                SET reminder_1h_sent = FALSE
                WHERE reminder_1h_sent IS NULL
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_interview_schedules_email_status 
                ON interview_schedules(candidate_email, status)
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS interview_feedback (
                    id SERIAL PRIMARY KEY,
                    interview_id INTEGER REFERENCES interview_schedules(id),
                    interviewer_id INTEGER,
                    technical_skills INTEGER,
                    communication_skills INTEGER,
                    problem_solving INTEGER,
                    cultural_fit INTEGER,
                    overall_rating INTEGER,
                    rating INTEGER,
                    strengths TEXT,
                    weaknesses TEXT,
                    recommendation VARCHAR(20),
                    detailed_feedback TEXT,
                    comments TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_tasks (
                    id SERIAL PRIMARY KEY,
                    candidate_email VARCHAR(255),
                    status VARCHAR(50),
                    offer_letter_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                INSERT INTO interviewers (id, name, email, timezone, is_active)
                VALUES (1, 'HR Team', 'workspace3705@gmail.com', 'Asia/Kolkata', TRUE)
                ON CONFLICT (email) DO NOTHING
            """)

            enable_demo_users = os.getenv('ENABLE_DEMO_USERS', 'false').lower() in ('1', 'true', 'yes', 'on')
            if enable_demo_users:
                from hashlib import sha256

                def hash_pwd(pwd):
                    return sha256(pwd.encode()).hexdigest()

                demo_users = [
                    ('admin', 'admin@example.com', hash_pwd('password'), 'hr'),
                    ('recruiter', 'recruiter@example.com', hash_pwd('password'), 'recruiter'),
                    ('john.smith', 'john.smith@company.com', hash_pwd('password'), 'recruiter'),
                ]

                for username, email, pwd_hash, role in demo_users:
                    cur.execute(
                        """
                        INSERT INTO users (username, email, password_hash, role, is_active)
                        VALUES (%s, %s, %s, %s, TRUE)
                        ON CONFLICT (email) DO NOTHING
                        """,
                        (username, email, pwd_hash, role)
                    )

            _run_sql_migrations(cur)
            _apply_schema_hotfixes(cur)

            print("Database initialized successfully with unified schema!")
            if enable_demo_users:
                print("✓ Demo users created for testing (admin@example.com, recruiter@example.com, john.smith@company.com)")
            conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()