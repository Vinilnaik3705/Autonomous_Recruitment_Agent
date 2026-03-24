# Architecture

## System components

The platform has four major layers:

1. Frontend UI (React/Vite)
2. Backend API (FastAPI)
3. Data layer (PostgreSQL)
4. Workflow orchestration (n8n)

## Frontend

Key behavior:

- Uses Axios client with base path `/api`
- Vite proxy forwards `/api/*` to backend port 8000
- Stores auth token in local storage and sends Bearer token
- Shows role-aware interfaces:
  - Candidate portal
  - Interviewer status view
  - Recruiter/super-admin HR panel

## Backend

Main API app:

- FastAPI app with CORS enabled
- Routers registered for auth, jobs, candidate, notifications, OA, email
- Startup hook runs DB initialization and migration logic
- Service modules initialize for scheduling, feedback, onboarding, and resume analysis

Core modules:

- `database.py`: connection logic with host/port fallback support
- `init_db.py`: schema creation, migration tracking, non-destructive hotfixes
- `services/`: business logic for scheduling, feedback, matching, onboarding, parsing
- `routers/`: API grouping by domain

## Data model (high-level)

Primary tables include:

- `users`
- `job_descriptions`
- `resume_files`
- `resume_data`
- `candidates`
- `interview_schedules`
- `interview_feedback`
- `onboarding_tasks`
- `notifications`
- `schema_migrations`

## AI and scoring flow

- Resume text is extracted from PDF/DOCX
- Candidate profile signals are parsed (name, email, phone, skills)
- Embeddings-based semantic score is computed against job description
- Threshold determines shortlist behavior (currently used in workflows)

## OA and interview orchestration

- OA launch links can include callback metadata
- OA completion callback or direct submit updates score in DB immediately
- Passing score triggers scheduling workflow webhook
- Interview lifecycle includes schedule, reminders, feedback kits, no-show checks, and decisions

## Deployment topology (local default)

- Postgres container: 5433:5432
- FastAPI container: 8000:8000
- n8n container: 5678:5678
- Frontend dev server: 5173 (outside compose)

## Design choices

- Idempotent DB initialization to support repeated startup
- Non-destructive schema compatibility updates for older DB states
- Background tasks for email/scheduling side-effects
- Multiple payload shape handling in OA callbacks for integration resilience
