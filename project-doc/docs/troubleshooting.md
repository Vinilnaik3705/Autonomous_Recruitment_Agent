# Troubleshooting

## Docker or service startup issues

Symptoms:

- Containers do not start
- API or frontend unreachable

Checks:

1. Confirm Docker Desktop is running
2. Rebuild and restart stack
3. Inspect container logs for postgres, fastapi, and n8n

## Port conflicts

If 3000, 5433, 5678, or 8000 are already in use:

1. Stop conflicting local processes
2. Bring compose stack down
3. Start compose stack again

## Database connectivity errors

Verify database settings used by fastapi:

- host: postgres
- port: 5432 (inside compose network)
- DB_NAME: hr_db
- DB_USER: hr_user

## Workflow trigger failures

Symptoms:

- scheduling or feedback automation not triggered

Checks:

1. Confirm n8n is reachable at port 5678
2. Verify webhook environment variables in fastapi service
3. Re-import private workflow JSON if workflows are missing

## Feedback form not loading

The backend serves feedback form from frontend/feedback-form.html first,
with fallback to backend/feedback-form.html.
If unavailable, verify both files are present in source and container image.
