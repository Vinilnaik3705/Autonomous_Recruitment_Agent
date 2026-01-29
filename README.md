# Autonomous Recruitment Agent

## ✅ Project Overview

This is an autonomous recruitment agent that helps with:
- Resume parsing and screening
- Candidate matching
- Automated interview scheduling
- Onboarding workflows

The system uses **FastAPI** for the backend, **PostgreSQL** for the database, and **n8n** for workflow orchestration.

---

## ✅ Prerequisites

*   Docker Desktop (installed and running)
*   Git

**That's it! You do NOT need to install Python, PostgreSQL, or any other dependencies manually.**

---

## ✅ Setup & Run (Standard Industry Way)

### 1. Clone the Repository
```bash
git clone <repo_url>
cd Autonomous_Recruitment_Agent
```

### 2. Configure Environment Variables
Copy the example environment file and fill in your keys:

```bash
cp .env.example .env
```

Open `.env` and set your `OPENAI_API_KEY`. The database URL and ports are pre-configured for Docker.

### 3. Run with Docker
Start the entire system with one command:

```bash
docker compose up -d --build
```

Docker will automatically:
- Download the Python image
- Install everything from `backend/requirements.txt`
- Create the Postgres container & volume
- Start FastAPI and n8n

### 4. Open Services

*   **FastAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **n8n Workflows**: [http://localhost:5678](http://localhost:5678)

### 5. Stop Services
To stop the containers:

```bash
docker compose down
```

---

## ✅ n8n Workflows
Since n8n workflows are stored in a Docker volume, they are not automatically synced. 

You can find the exported workflow JSON files in the `n8n_workflows/` folder (if available).
To use them:
1. Open n8n at `http://localhost:5678`.
2. Go to **Workflows** > **Import**.
3. Select the `.json` files from `n8n_workflows/`.

---

## ✅ File Structure

*   `backend/requirements.txt`: Python dependencies (installed automatically by Docker).
*   `backend/Dockerfile`: Instructions to build the backend image.
*   `docker-compose.yml`: Defines how to run Postgres, FastAPI, and n8n together.
*   `.env.example`: Template for environment variables.
