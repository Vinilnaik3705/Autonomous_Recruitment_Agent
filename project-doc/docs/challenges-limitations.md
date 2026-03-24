# Challenges and Limitations

## Challenges faced during implementation

### 1) OA callback reliability

Challenge:

- External OA providers do not always push completion data in a consistent, automatic way.

What was done:

- Added direct OA result submission endpoints.
- Added callback endpoint that can parse multiple payload formats.
- Added score extraction from URL/page patterns.

### 2) Schema drift across environments

Challenge:

- Existing databases had different schema versions and missing columns.

What was done:

- Startup migrations table added.
- Non-destructive ALTER and backfill hotfix logic added.
- Compatibility handling for legacy columns (example: notification read fields).

### 3) Integration complexity with n8n

Challenge:

- Multiple moving pieces: webhook URLs, payload shape, and environment connectivity.

What was done:

- Added proxy and integration-safe payload mapping.
- Added fallback behavior and explicit logging around webhook calls.

### 4) Long-running AI dependencies

Challenge:

- Embedding model downloads can fail in restricted networks.

What was done:

- Docker build pre-downloads sentence-transformer model.

### 5) Balancing async side effects with fast API response

Challenge:

- Email and scheduling side effects can slow response or fail independently.

What was done:

- Moved side effects to background tasks where possible.

## Current limitations

### Security limitations

- Sensitive keys/secrets handling is not fully hardened.
- Default/fallback secret key behavior is unsafe for production if unchanged.
- CORS is currently broad and should be restricted.

### Reliability limitations

- Some workflows still depend on external webhook availability.
- OA score extraction from external pages is best-effort and can break if provider HTML changes.

### Product limitations

- Candidate portal has partial business context in some fields.
- Analytics/reporting depth is currently limited.
- Onboarding flow is initiated but not full lifecycle-managed in this repository.

### Engineering limitations

- Limited formal automated test coverage.
- No complete CI/CD quality gate documented yet.

## Recommended next milestones

1. Security hardening sprint (secrets, CORS, token policy, RBAC audit).
2. Testing sprint (unit/integration/e2e with CI).
3. Observability sprint (logs, metrics, health checks, alerting).
4. Workflow resilience sprint (retry/dead-letter/idempotency around webhooks).
