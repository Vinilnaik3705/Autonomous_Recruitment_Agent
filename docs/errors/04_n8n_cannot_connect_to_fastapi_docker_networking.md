# Error 04: N8N Cannot Connect to FastAPI Backend (404 / Connection Refused)

## Symptom
Inside an n8n HTTP Request node that calls the FastAPI backend, the request fails with:
```
Error: connect ECONNREFUSED 127.0.0.1:8000
```
or
```
404 Not Found
```
even though FastAPI is running and accessible from the browser.

## Root Cause — Docker Networking
When **n8n runs inside Docker**, `localhost` or `127.0.0.1` inside the container does **NOT** refer to your host machine. It refers to the container itself. Since FastAPI is not running inside the n8n container, the connection is refused.

```
❌ n8n container → localhost:8000  (goes to itself, nothing there)
✅ n8n container → host.docker.internal:8000  (goes to your host machine)
✅ n8n container → backend:8000  (if both are in the same docker-compose network)
```

## Solution

### Option A — Use `host.docker.internal` (Easiest)
In n8n HTTP Request nodes, replace `localhost` with `host.docker.internal`:

```
Before: http://localhost:8000/resume/score-with-embeddings
After:  http://host.docker.internal:8000/resume/score-with-embeddings
```

> **Note:** `host.docker.internal` works on Windows and macOS. On Linux, add `extra_hosts` to docker-compose (see below).

### Option B — Use Docker Service Name (Recommended for docker-compose)
If FastAPI and n8n are in the same `docker-compose.yml`, use the service name directly:

```yaml
# docker-compose.yml
services:
  backend:
    container_name: fastapi_backend
    ...
  n8n:
    container_name: n8n
    ...
```

Then in n8n, call:
```
http://backend:8000/resume/score-with-embeddings
```

Docker's internal DNS resolves `backend` to the correct container IP.

### Option C — Linux Host Fix in docker-compose.yml
On Linux, `host.docker.internal` doesn't work by default. Add this to the n8n service:

```yaml
services:
  n8n:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Common Mistake — Hardcoded localhost in n8n Node
When you see this in an n8n Code/HTTP node:
```javascript
const url = "http://localhost:8000/api/jobs";  // ❌ WRONG in Docker
const url = "http://backend:8000/api/jobs";    // ✅ CORRECT in docker-compose
```

## Key Lesson
> Inside Docker, `localhost` = the container, NOT your machine. Use the **Docker service name** (e.g., `backend`) when both services share the same `docker-compose.yml`.
