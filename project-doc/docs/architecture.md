# Architecture

## High-level flow

1. User actions come from frontend dashboard
2. Frontend calls FastAPI endpoints
3. FastAPI reads/writes PostgreSQL and triggers n8n webhooks
4. n8n orchestrates emails, reminders, and external automations

## Backend modules

- Routers: auth, candidate, email, job, notification
- Services: resume processing, matching, scheduling, feedback, onboarding
- Agents: resume analyzer for LLM-assisted extraction and summary
- Migrations: SQL schema evolution under backend/migrations

## Data and state

PostgreSQL is the system of record for:

- jobs and candidates
- interview schedules and statuses
- interviewer feedback and recommendations
- onboarding lifecycle state

## Deployment shape in docker-compose

- postgres service with healthcheck and persistent volume
- fastapi service with startup DB init and app launch
- n8n service using postgres backend and webhook exposure

## Integration notes

- FastAPI startup initializes DB tables and service singletons
- Scheduling and feedback flows can trigger n8n webhooks
- Frontend feedback form can be served through backend endpoint
