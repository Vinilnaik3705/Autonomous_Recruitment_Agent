# Autonomous Recruitment Agent

This documentation explains the current, production-facing structure of the project.

## What this platform does

The system automates the hiring lifecycle in five phases:

1. Resume intake and AI analysis
2. Candidate-job matching and shortlisting
3. Interview scheduling and status tracking
4. Interview feedback collection and decisioning
5. Onboarding initiation

## Runtime components

- Frontend: React + Vite dashboard on port 3000
- Backend: FastAPI service on port 8000
- Database: PostgreSQL on port 5433 (container mapped)
- Workflow engine: n8n on port 5678

## Source layout

- backend: API, business logic, migrations, service layer
- frontend: UI pages, dashboard components, API client
- docker-compose.yml: local container orchestration
- project-doc: MkDocs documentation source

## Security boundary

n8n workflow JSON files are intentionally not stored in this public repository.
They are managed in a private repository for authorized team members only.

Continue with Getting Started for setup steps and Backend API for endpoint-level details.
