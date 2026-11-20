# Autonomous Recruitment Agent

This migration branch serves a single recruitment team's dashboard. Staff submit a PDF or DOCX, a job description, required skills and an invitation address. Candidates register, claim an emailed invitation and view their own stage and checklist. HR approves offers and rejections. A screening score informs human review.

## Local deployment

1. Install Docker Engine or Docker Desktop with Compose v2. Copy `.env.example` to `.env`. Set independent random hex values for `POSTGRES_PASSWORD` and `JWT_SECRET` (at least 32 bytes each). Leave `INTERNAL_API_KEY` empty unless a trusted service needs HR access.
2. Set `GEMINI_API_KEY`, or set `LLM_PROVIDER=ollama` and point `OLLAMA_BASE_URL` at a server reachable by the heavy worker with `OLLAMA_MODEL` installed. MiniLM downloads its model on the first screening run. Allow outbound model downloads or provision the worker's Hugging Face cache in advance.
3. In the Google Cloud project enable Calendar and Gmail, configure the OAuth consent screen and authorize the recruitment test mailbox with Calendar and Gmail send access. Save the authorized-user JSON with a refresh token as `secrets/google-token.json`. On the operator’s desktop, install `google-auth-oauthlib` and run `python scripts/authorize_google.py /path/to/desktop-client.json` to open the consent screen and create the token file. Grant the runtime user read access to the mounted file. Set `GOOGLE_CALENDAR_ID` to the shared test calendar or `primary`. The authorized mailbox must have calendar write access. Use a dedicated test recipient for the first submission. Submitting queues an actual invitation.
4. Run `docker compose up --build -d`. The migration service must exit successfully. Open <http://localhost:3000> and check <http://localhost:8000/health>. Use `docker compose logs migrate api heavy light beat` for diagnostics.
5. Register the first account through the dashboard. An administrator must verify the account and promote it using `docker compose exec postgres psql -U recruitment -d recruitment`. Use the query below with the registered address, confirm the one returned row and sign in. Public registration grants candidate access only.

```sql
UPDATE users SET role = 'hr' WHERE email = 'your-verified-address@example.org'
RETURNING id, email, role;
```

## Workflow

The Vite dashboard calls FastAPI (`backend.pipeline_api:app`). PostgreSQL owns the run, pending work, approval and delivery state. Celery Beat republishes due work to Redis every 15 seconds. The heavy worker locks the run, invokes the parse/extract/embed LangGraph, compares the resume to the job with MiniLM, stores its vector and releases the uploaded bytes after success. Failed screening retains the document for retry. Staff see extracted fields, score components, stages and delivery state. This deployment assumes one HR team. Staff can view that team's applications.

The light worker sends invitations, interviews, reminders, approved offers and onboarding checklists. Calendar booking uses a stable event ID and rescheduling updates that event. A candidate must possess both the invitation code and an account with the addressed email. Candidates see stages and checklists after linking. Gmail sends cannot guarantee exactly-once delivery after a lost response. The worker records ambiguous sends as `uncertain`; inspect the sender's Sent folder or calendar before reconciliation. An outstanding calendar or offer action blocks the next stage until reconciled. HR can use the API docs to submit `POST /actions/{id}/reconcile` with the verification evidence, delivery disposition and Google event or message ID if delivered. Confirming non-delivery requeues the action. Keep one Beat instance.

The dashboard polls every 15 seconds and displays the latest 100 staff runs. Reviewers can shortlist, schedule or reschedule, record interview feedback and advance a candidate. Enter the actual offer terms before confirming an offer. HR records acceptance before beginning onboarding and records checklist verification before completion. This version does not collect a candidate e-signature.

## Hosted deployment

Use the root `render.yaml` Blueprint for managed PostgreSQL, Redis-compatible storage, the API, two workers and Beat. Provision enough RAM for the heavy worker to load CPU PyTorch and MiniLM. The API pre-deploy command runs Alembic. Place the authorized-user JSON in a Render secret file named `google-token.json` on the API and light worker. Configure the exact frontend origin in `CORS_ORIGINS`. Review the paid service choices before provisioning.

Import the repository in Vercel with root directory `frontend`, Vite, Node 22, install command `npm ci`, build command `npm run build` and output directory `dist`. Set `VITE_API_BASE_URL` to the public HTTPS API origin before building. API secrets belong exclusively on the backend. Verify the API health route, sign in and use an anonymized resume and designated test mailbox for the hosted smoke test.

## Existing databases and rollback

The Compose project creates its own database volume. Before connecting an existing installation, create a backup using `pg_dump -Fc`, restore it into a separate PostgreSQL 16 instance with pgvector, and run `alembic -c backend/alembic.ini upgrade head` against the restored copy. Compare existing row counts and check an existing login. The new runs table starts empty. Historical n8n applications are not imported into the new stage history. Retain the existing deployment and database until acceptance. An Alembic downgrade deletes migration tables and their data.

## Verification

From the repository root, install `backend/requirements.txt`, pytest, httpx and pytest-cov using Python 3.11. Set `JWT_SECRET`, `INTERNAL_API_KEY`, `DATABASE_URL` and `REDIS_URL` to test-only values. Use a disposable database for the integration suite.

```sh
alembic -c backend/alembic.ini upgrade head
PIPELINE_INTEGRATION=1 python -m pytest
cd frontend
npm ci
npm run lint
npm test
npm run build
```

The integration test exercises real JWT issuance, PostgreSQL, pgvector, LangGraph, duplicate submission, repeated task delivery, role checks, rescheduling, feedback, offer approval and onboarding. It substitutes model outputs and Google calls. Live signoff also requires matching Calendar event IDs after rescheduling, one received message per intended action and worker processing through Redis. Archived source for the legacy stack remains in the branch for comparison. The migrated deployment uses the entry points above.

### Live Google acceptance

Mount the authorized-user token, set `GOOGLE_TEST_RECIPIENT` to an approved test mailbox, and set `GOOGLE_CALENDAR_ID` to the designated test calendar. Run `python -m scripts.google_smoke` from the repository root in the configured backend environment. This sends real test invitations and one email, verifies the rescheduled event through Calendar, and cleans up the synthetic event it created. Confirm receipt in the designated mailbox. Keep OAuth tokens outside Git and chat.

## Project documentation

- [Technical report (PDF)](project-doc/demo/recruitment-report.pdf)
- [Demo presentation (PowerPoint)](project-doc/demo/recruitment-demo.pptx)
- [Verification record and demo script](project-doc/docs/status.md)
- [Report and presentation source](project-doc/demo/)
