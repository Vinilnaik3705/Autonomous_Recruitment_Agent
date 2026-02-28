from backend.database import get_db_connection

def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Users
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

            # Job Descriptions (session isolation - each screening session gets a unique job_id)
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

            # Ensure created_at exists for older tables
            cur.execute("""
                ALTER TABLE job_descriptions
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)

            # Readable view for easier inspection in psql
            cur.execute("""
                CREATE OR REPLACE VIEW job_descriptions_readable AS
                SELECT
                    job_id,
                    title,
                    regexp_replace(description, '\\s+', ' ', 'g') AS description,
                    regexp_replace(required_skills, '\\s+', ' ', 'g') AS required_skills,
                    min_experience,
                    max_experience,
                    created_at
                FROM job_descriptions
                ORDER BY created_at DESC;
            """)
            
            # Interviewers
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

            # Resume Files (file upload tracking)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS resume_files (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    filename VARCHAR(255) NOT NULL,
                    file_size INTEGER,
                    file_type VARCHAR(20),
                    file_hash VARCHAR(64),
                    processed BOOLEAN DEFAULT FALSE,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id VARCHAR(50)
                )
            """)

            # Add file_hash column for existing tables
            cur.execute("""
                ALTER TABLE resume_files
                ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);
            """)

            # Remove duplicate resume_files entries per session (keep most recent)
            cur.execute("""
                DELETE FROM resume_files
                WHERE id NOT IN (
                    SELECT DISTINCT ON (session_id, file_hash) id
                    FROM resume_files
                    WHERE file_hash IS NOT NULL
                    ORDER BY session_id, file_hash, upload_date DESC
                );
            """)

            # Enforce uniqueness on (session_id, file_hash) to prevent duplicates
            cur.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS resume_files_session_file_hash_uniq
                ON resume_files (session_id, file_hash)
                WHERE file_hash IS NOT NULL;
            """)

            # Resume Data (parsed resume content)
            # job_id ties each resume to a specific screening session
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
                    email_sent BOOLEAN DEFAULT FALSE,
                    sample_oa_sent BOOLEAN DEFAULT FALSE,
                    sample_oa_sent_at TIMESTAMP,
                    official_oa_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Add OA tracking columns for existing tables
            cur.execute("""
                ALTER TABLE resume_data
                ADD COLUMN IF NOT EXISTS email_sent BOOLEAN DEFAULT FALSE;
            """)
            
            cur.execute("""
                ALTER TABLE resume_data
                ADD COLUMN IF NOT EXISTS sample_oa_sent BOOLEAN DEFAULT FALSE;
            """)
            
            cur.execute("""
                ALTER TABLE resume_data
                ADD COLUMN IF NOT EXISTS sample_oa_sent_at TIMESTAMP;
            """)
            
            cur.execute("""
                ALTER TABLE resume_data
                ADD COLUMN IF NOT EXISTS official_oa_sent BOOLEAN DEFAULT FALSE;
            """)

            # Drop existing constraints with any name pattern
            cur.execute("""
                DO $$
                BEGIN
                    BEGIN
                        ALTER TABLE resume_data DROP CONSTRAINT resume_data_job_id_email_key CASCADE;
                    EXCEPTION WHEN UNDEFINED_OBJECT THEN
                        NULL;
                    END;
                    
                    BEGIN
                        ALTER TABLE resume_data DROP CONSTRAINT resume_data_job_id_email_unique CASCADE;
                    EXCEPTION WHEN UNDEFINED_OBJECT THEN
                        NULL;
                    END;
                    
                    BEGIN
                        ALTER TABLE resume_data DROP CONSTRAINT resume_data_job_id_email CASCADE;
                    EXCEPTION WHEN UNDEFINED_OBJECT THEN
                        NULL;
                    END;
                END $$;
            """)

            # Remove duplicate resume_data entries (keep the one with highest ai_score and latest created_at)
            cur.execute("""
                DELETE FROM resume_data 
                WHERE id NOT IN (
                    SELECT DISTINCT ON (job_id, email) id 
                    FROM resume_data 
                    ORDER BY job_id, email, ai_score DESC, created_at DESC
                );
            """)

            # Re-add the UNIQUE constraint to prevent future duplicates
            cur.execute("""
                ALTER TABLE resume_data
                ADD CONSTRAINT resume_data_job_id_email_unique UNIQUE (job_id, email);
            """)

            # Candidates (workflow tracking - OA, reminders, shortlisting)
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

            # Interview Schedules
            cur.execute("""
                CREATE TABLE IF NOT EXISTS interview_schedules (
                    id SERIAL PRIMARY KEY,
                    candidate_name VARCHAR(100),
                    candidate_email VARCHAR(100),
                    interviewer_id INTEGER REFERENCES interviewers(id),
                    scheduled_time TIMESTAMP,
                    duration_minutes INTEGER DEFAULT 30,
                    meeting_link TEXT,
                    status VARCHAR(20) DEFAULT 'scheduled',
                    google_event_id VARCHAR(255),
                    feedback_submitted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for faster duplicate checking
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_interview_schedules_email_status 
                ON interview_schedules(candidate_email, status)
            """)

            # Interview Feedback
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

            # Onboarding Tasks
            cur.execute("""
                CREATE TABLE IF NOT EXISTS onboarding_tasks (
                    id SERIAL PRIMARY KEY,
                    candidate_email VARCHAR(255),
                    status VARCHAR(50),
                    offer_letter_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert default interviewer if none exists
            cur.execute("""
                INSERT INTO interviewers (id, name, email, timezone, is_active)
                VALUES (1, 'HR Team', 'workspace3705@gmail.com', 'Asia/Kolkata', TRUE)
                ON CONFLICT (email) DO NOTHING
            """)

            # Insert demo users for testing RBAC
            from hashlib import sha256
            def hash_pwd(pwd):
                return sha256(pwd.encode()).hexdigest()
            
            demo_users = [
                ('admin', 'admin@example.com', hash_pwd('password'), 'super_admin'),
                ('recruiter', 'recruiter@example.com', hash_pwd('password'), 'recruiter'),
                ('interviewer', 'interviewer@example.com', hash_pwd('password'), 'interviewer'),
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

            print("Database initialized successfully with unified schema!")
            print("✓ Demo users created for testing (admin@example.com, recruiter@example.com, interviewer@example.com)")
            conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
