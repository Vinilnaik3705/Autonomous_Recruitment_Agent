# Troubleshooting

## Backend does not start

Symptoms:

- Uvicorn exits on startup.

Checks:

1. Verify Python dependencies are installed.
2. Confirm DB is reachable on configured host/port.
3. Confirm `secrets.toml` or env vars are valid.
4. Check startup logs for migration SQL errors.

## Database connection issues

Symptoms:

- Connection refused or timeout.

Checks:

1. Confirm Postgres container is healthy.
2. Confirm host port mapping is `5433:5432` when using compose.
3. Validate DB credentials.
4. Use psql to test direct connection.

## Frontend API calls fail

Symptoms:

- Network error, CORS error, or 404 on API routes.

Checks:

1. Confirm backend is on `http://127.0.0.1:8000`.
2. Confirm frontend runs with Vite proxy enabled.
3. Confirm requests go to `/api/...` from frontend.
4. Inspect browser devtools network tab for failing URL.

## OA score not updating

Symptoms:

- Candidate completed OA but no score in DB.

Checks:

1. Call `POST /oa/submit-result` manually to verify path.
2. Confirm candidate email exists in applicant table.
3. Check OA callback payload includes email and score/report URL.
4. Check backend logs for score parsing warnings.

## Emails not being delivered

Symptoms:

- Email endpoint returns template but recipient never receives message.

Checks:

1. Verify email sending is enabled by configuration.
2. Verify SMTP/Brevo credentials are valid.
3. Check blocked/test email pattern settings.
4. Check backend logs for SMTP error messages.

## n8n workflow not triggering

Symptoms:

- Scheduling or screening automation not firing.

Checks:

1. Confirm n8n is running on expected URL/port.
2. Confirm webhook URL matches backend/frontend configuration.
3. Confirm workflow is active (not only saved).
4. Test webhook manually with sample payload.

## Useful verification commands

```bash
# Backend docs
curl http://127.0.0.1:8000/docs

# Build docs
cd project-doc
mkdocs build

# Check compose service health
docker compose ps
```
