# Getting Started

## Prerequisites

- Docker Desktop installed and running
- Git
- OpenAI API key

## 1. Clone and configure

1. Clone the repository
2. Copy environment template
3. Add your OpenAI key

Example:

- Copy .env.example to .env
- Set OPENAI_API_KEY in .env

## 2. Start services

Run docker compose with build enabled.

Expected exposed ports:

- 3000: frontend
- 8000: FastAPI docs and API
- 5678: n8n editor and webhooks
- 5433: PostgreSQL

## 3. Validate startup

- Open frontend dashboard at http://localhost:3000
- Open API docs at http://localhost:8000/docs
- Open n8n at http://localhost:5678

## 4. Initialize workflow assets

Workflow JSON files are maintained privately.
Import the workflow exports from the private workflow repository into n8n.

## 5. Stop stack

Use docker compose down for normal stop.
Use docker compose down -v to remove volumes including database state.
