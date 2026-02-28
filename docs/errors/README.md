# Error Documentation — Automated Recruitment System

This folder contains documentation for the most important errors encountered during development of the **Automated Recruitment System** (FastAPI + n8n + PostgreSQL + React).

Each file describes:
- The exact error message or symptom
- The root cause
- The solution applied
- Key lessons learned

---

## Index

| # | File | Error Summary |
|---|---|---|
| 01 | [N8N Webhook 404 Not Registered](./01_n8n_webhook_404_not_registered.md) | Production webhook doesn't exist because workflow is Inactive |
| 02 | [Only First Resume Processed in Bulk](./02_only_first_resume_processed_in_bulk.md) | N8N workflow only processes item[0] from an uploaded array |
| 03 | [Scoring Model Fails to Load in Docker](./03_scoring_model_fails_to_load_in_docker.md) | SentenceTransformer model can't download/initialize inside Docker container |
| 04 | [N8N Cannot Connect to FastAPI (Docker Networking)](./04_n8n_cannot_connect_to_fastapi_docker_networking.md) | `localhost` inside Docker points to the container, not the host |
| 05 | [N8N Expression Mode OFF](./05_n8n_expression_mode_off_literal_text_sent.md) | `{{$json['email']}}` sent as literal text instead of resolved value |
| 06 | [N8N Loop Data Poisoning](./06_n8n_loop_data_poisoning.md) | Loop feedback corrupts `$json` context in loop nodes |
| 07 | [Resume Scores Too Low](./07_resume_scores_too_low_wrong_algorithm.md) | Jaccard similarity gives near-zero scores; fixed with embeddings |
| 08 | [Double /api/ Path in API Calls](./08_double_api_path_causing_404.md) | Frontend constructs `/api/api/jobs` URL causing 404s |

---

## Most Critical Errors (by Impact)

1. **Error 03** — Scoring model failure → All scores are 0, core functionality broken
2. **Error 01** — Webhook 404 → Resume upload completely fails
3. **Error 02** — Only first resume processed → Bulk screening broken
4. **Error 04** — Docker networking → n8n cannot call backend at all

---

## Technology Stack Covered
- **FastAPI** (Python backend)
- **n8n** (workflow automation)
- **PostgreSQL** (database)
- **React + Vite** (frontend)
- **Docker + docker-compose** (containerization)
- **SentenceTransformers** (ML scoring)
