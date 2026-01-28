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

            # Resume Files
            cur.execute("""
                CREATE TABLE IF NOT EXISTS resume_files (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    filename VARCHAR(255) NOT NULL,
                    file_size INTEGER,
                    file_type VARCHAR(20),
                    processed BOOLEAN DEFAULT FALSE,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id VARCHAR(50),
                    UNIQUE(user_id, filename)
                )
            """)

            # Resume Data
            cur.execute("""
                CREATE TABLE IF NOT EXISTS resume_data (
                    id SERIAL PRIMARY KEY,
                    resume_file_id INTEGER REFERENCES resume_files(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id),
                    candidate_name VARCHAR(100),
                    candidate_email VARCHAR(100),
                    candidate_phone VARCHAR(50),
                    skills TEXT,
                    education TEXT,
                    extracted_text TEXT,
                    interview_status VARCHAR(20),
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(resume_file_id)
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
                    status VARCHAR(20) DEFAULT 'scheduled',
                    google_event_id VARCHAR(255),
                    feedback_submitted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Interview Feedback
            cur.execute("""
                CREATE TABLE IF NOT EXISTS interview_feedback (
                    id SERIAL PRIMARY KEY,
                    interview_id INTEGER REFERENCES interview_schedules(id),
                    interviewer_id INTEGER REFERENCES interviewers(id),
                    technical_skills INTEGER,
                    communication_skills INTEGER,
                    problem_solving INTEGER,
                    cultural_fit INTEGER,
                    overall_rating INTEGER,
                    strengths TEXT,
                    weaknesses TEXT,
                    recommendation VARCHAR(20),
                    detailed_feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            print("Database initialized successfully!")
            conn.commit()
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
