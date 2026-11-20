# Autonomous Recruitment Agent

FastAPI and Vite provide the hiring workspace. PostgreSQL stores the workflow, uploaded resumes and 384-dimensional MiniLM vectors. Redis and Celery dispatch background work. Gmail and Calendar use an operator-authorized Google account.

## Start a fresh local database

Copy `.env.example` to `.env`. Set `POSTGRES_PASSWORD`, put the same password in `DATABASE_URL`, and set a `JWT_SECRET` of at least 32 bytes. A random hex password works directly in the connection URL. Set the LLM provider settings for Gemini or a reachable Ollama server. For a clean start from this branch, use a disposable Compose project or the documented fresh-volume procedure.

```sh
docker compose up -d --build
curl http://localhost:3000/api/health
docker compose exec api python -m backend.db.migrate
docker compose exec postgres psql -U recruitment -d recruitment -c '\dt' -c '\d applications'
```

The second migration run prints `No pending migrations.` PostgreSQL uses the `recruitment_data` named volume. `docker compose down -v` deletes that volume. Existing databases from the Alembic branch need a separate fresh database for the new schema.

Create privileged accounts from the deployment terminal. Self-registration always creates a candidate.

```sh
docker compose exec api python -m backend.create_staff hr@example.org "HR Test"
docker compose exec api python -m backend.create_staff panel@example.org "Panel Test" --role interviewer
```

Sign in at http://localhost:3000. Create an open job, then upload a synthetic PDF or DOCX. Wait for the worker to calculate the score. Candidates can submit their own application or claim a staff-uploaded application using the emailed invitation.

## Database layout

| Table | Purpose |
| --- | --- |
| schema_migrations | Lists the SQL files already applied. |
| users | Stores password hashes and account roles. |
| jobs | Stores job specifications and their embeddings. |
| applications | Stores the resume reference, score, hiring status and offer information for one candidate and job. |
| interviews | Stores scheduling, interviewer assignment and feedback. |
| onboarding_tasks | Tracks checklist progress after an offer. |
| agent_runs | Records workflow changes and outbound work, including claims and provider receipts. |

Numbered SQL files under `backend/db/migrations/` own all schema changes. Add a new file for changes to an already-applied schema. The API borrows connections from one pool per process. Workers use independent database connections. Resumes are PostgreSQL large objects referenced by `resume_path`; include large objects when taking or restoring a backup. Normal application removal is through a soft-delete design. Any future hard-delete routine must also unlink the corresponding large object.

Claims and delivery records are persisted before contacting Google. When Google may have accepted an action but the worker has no receipt, the run is marked uncertain. HR must verify the outcome and reconcile it through `POST /actions/{id}/reconcile` before retrying. Calendar uses one team calendar.

## Deploy

Use `render.yaml` to configure the API, PostgreSQL, Redis, and Celery services with a fresh database. The API pre-deploy command applies the SQL migrations. Configure the LLM provider for the relevant services and set API CORS to the frontend origin. Deploy the `frontend` directory to Vercel with `VITE_API_BASE_URL` set to the API URL.

Google setup requires an enabled Gmail and Calendar API, a Desktop OAuth client and an authorized test account. On your desktop install `google-auth-oauthlib`, then run `python scripts/authorize_google.py /path/to/desktop-client.json`. Mount the generated `google-token.json` at the configured `GOOGLE_TOKEN_FILE` path. On Render use a secret file of that name on the API and light worker. Set `GOOGLE_CALENDAR_ID` to a writable test calendar. Set `GOOGLE_TEST_RECIPIENT` and run `python -m scripts.google_smoke` from the repository root in the configured environment.

The rebuild uses local JWT sign-in. Prior Supabase identities have no automatic transfer. The old standalone OA and payment workflows and n8n automation have no equivalent in the new API. The new workflow schedules one interview round in the dashboard, supports assigned-interviewer feedback, and tracks onboarding checklist submission and verification. Multi-round scheduling, feedback reminder automation, and onboarding document uploads are still separate implementation work.
