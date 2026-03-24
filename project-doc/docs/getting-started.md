# Getting Started

This guide helps a completely new user run the project on a local machine.

## Prerequisites

Install the following before running:

- Git
- Python 3.11+
- Node.js 18+
- npm 9+
- Docker Desktop (recommended for full stack)
- Docker Compose (bundled with Docker Desktop)

Optional but recommended:

- PostgreSQL client (psql) for DB checks
- n8n knowledge for workflow imports/customization

## Clone and open

```bash
git clone <your-repo-url>
cd automated_res
```

## Environment and secrets

The project reads config from environment variables and/or `secrets.toml`.

Minimum required values for local development:

- Database connection details (host, user, password, db name, port)
- `SECRET_KEY` for JWT signing
- OA and scheduling webhook URLs (if workflow automation is enabled)
- Email SMTP/Brevo settings for real email delivery

Important security note:

- Do not commit real API keys or OAuth client secrets.
- Rotate any credential that was ever committed to version control.

## Option A: Run with Docker Compose (recommended)

From repository root:

```bash
docker compose up --build
```

This starts:

- PostgreSQL on host port `5433`
- FastAPI backend on port `8000`
- n8n on port `5678`

Then run frontend separately:

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL:

- http://localhost:5173

Backend docs:

- http://127.0.0.1:8000/docs

n8n UI:

- http://localhost:5678

## Option B: Run services manually (without Docker for backend/frontend)

### 1) Start PostgreSQL

Use local Postgres and create database/user matching your config.

### 2) Backend setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
python backend/init_db.py
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3) Frontend setup

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend uses Vite proxy `/api -> http://127.0.0.1:8000`.

### 4) Optional n8n setup

You can still run n8n via Docker:

```bash
docker compose up n8n postgres
```

## First run validation checklist

1. Open backend swagger: `http://127.0.0.1:8000/docs`
2. Open frontend: `http://localhost:5173`
3. Confirm DB tables were created on startup
4. Test auth endpoints (`/auth/register`, `/auth/login`)
5. Test one resume upload/analyze flow
6. Test OA score submission endpoint

## Running documentation locally

From `project-doc` directory:

```bash
mkdocs serve
```

Build static site:

```bash
mkdocs build
```

## Minimal successful run path for a new user

1. Start Docker Compose stack.
2. Start frontend with `npm run dev`.
3. Register/login in UI.
4. Create job description.
5. Upload resumes and screen.
6. Trigger OA invitation and submit OA result.
7. Check interview scheduling and status.
