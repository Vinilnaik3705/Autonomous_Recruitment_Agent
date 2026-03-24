# Project Overview

## Goal

Build a single platform that automates major HR pipeline steps from resume intake to onboarding, while keeping humans in control of final decisions.

## High-level capabilities

- Resume parsing from uploaded files
- AI-based matching against job descriptions using embeddings
- Candidate tracking and status timelines
- OA invitation, completion callback handling, and score persistence
- Automatic scheduling trigger for passing OA scores
- Interview scheduling, reminders, no-show handling, and rescheduling
- Interview feedback collection and decision routing
- Onboarding initiation after final decision
- Role-based access for recruiter, interviewer, candidate, and super admin

## Technology stack

- Frontend: React + Vite + Axios
- Backend: FastAPI + Pydantic + Uvicorn
- Database: PostgreSQL (with startup migrations and hotfixes)
- Workflow Orchestration: n8n
- AI/ML: sentence-transformers and OpenAI-integrated services
- Containerization: Docker + Docker Compose

## Repository structure summary

- backend: API, business logic, migrations, and services
- frontend: recruiter and candidate UI
- docker: Postgres initialization scripts
- project-doc: MkDocs documentation
- workflow JSON files: n8n flow definitions and fixes

## Who should use these docs

- New developers onboarding to this repository
- Recruiter ops engineers deploying locally or in staging
- QA users validating OA/interview workflows
- Contributors extending modules or debugging integration issues
