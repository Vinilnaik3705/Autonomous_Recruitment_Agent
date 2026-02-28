-- Migration for RBAC System
-- Adds role-based access control tables and columns

-- Extend users table with role information
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'recruiter',
    ADD COLUMN IF NOT EXISTS workspace_id INTEGER,
    ADD COLUMN IF NOT EXISTS department VARCHAR(100),
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS last_login TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    permissions TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_roles junction table for future extensibility
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Create candidate_assignments table (tie candidates to interviewers)
CREATE TABLE IF NOT EXISTS candidate_assignments (
    id SERIAL PRIMARY KEY,
    candidate_id INTEGER REFERENCES resume_data(id) ON DELETE CASCADE,
    interviewer_id INTEGER REFERENCES interviewers(id) ON DELETE CASCADE,
    assigned_by INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'assigned',
    UNIQUE(candidate_id, interviewer_id)
);

-- Create audit_log table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    old_value TEXT,
    new_value TEXT,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert core roles
INSERT INTO roles (name, description, permissions) VALUES
    ('super_admin', 'Full access to all features and settings', 
     ARRAY['upload_resumes', 'write_jd', 'upload_jd', 'run_screening', 'view_scores', 
           'manage_interviews', 'submit_feedback', 'view_analytics', 'manage_users', 
           'manage_settings', 'view_audit_log']),
    ('recruiter', 'Can manage resumes, JDs, and run screening', 
     ARRAY['upload_resumes', 'write_jd', 'upload_jd', 'run_screening', 'view_scores', 
           'manage_interviews', 'submit_feedback', 'view_analytics']),
    ('interviewer', 'Can only view assigned candidates and submit feedback', 
     ARRAY['view_assigned_candidates', 'submit_feedback', 'view_assigned_feedback']),
    ('candidate', 'Self-service portal - limited to own application', 
     ARRAY['upload_resume', 'check_status', 'join_interview'])
ON CONFLICT (name) DO NOTHING;

-- Create index for faster audit lookups
CREATE INDEX IF NOT EXISTS idx_audit_log_user_timestamp 
    ON audit_log(user_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_candidate_assignments_interviewer 
    ON candidate_assignments(interviewer_id);

CREATE INDEX IF NOT EXISTS idx_candidate_assignments_candidate 
    ON candidate_assignments(candidate_id);

-- Create index on users role for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_role 
    ON users(role);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'RBAC system migration completed successfully!';
    RAISE NOTICE 'Roles table initialized with 4 core roles.';
END $$;
