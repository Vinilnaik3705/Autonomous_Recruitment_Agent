# Error 08: Double /api/ Path in API Calls (404 on Deployed Frontend)

## Symptom
API calls result in a **double `/api`** path in the URL and produce 404 errors:

```
# What was being called:
https://your-backend.com/api/api/jobs

# What should be called:
https://your-backend.com/api/jobs
```

This worked fine on `localhost` but broke when deploying to a cloud/staging environment.

## Root Cause — URL Construction Logic
The `api.js` config file was building the base URL incorrectly. The environment variable `VITE_BACKEND_URL` was set to include `/api` at the end, AND the API calls in the code also appended `/api`:

```javascript
// ❌ Bug: VITE_BACKEND_URL = "https://backend.com/api"
// AND calls in components were doing:
const url = `${BASE_URL}/api/jobs`;  // → https://backend.com/api/api/jobs
```

## Solution

### Fix — Separate Base URL from API Prefix

```javascript
// frontend/src/config/api.js

// Base URL = domain only, no trailing /api
const BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

// Remove trailing slash if present
const cleanBase = BASE_URL.replace(/\/$/, '');

// All API calls use /api prefix here, not in the env var
export const API_ENDPOINTS = {
    jobs:        `${cleanBase}/api/jobs`,
    resumes:     `${cleanBase}/api/resumes`,
    batchScreen: `${cleanBase}/api/jobs/batch-screen`,
};
```

**Environment variable should be set as:**
```
VITE_BACKEND_URL=https://your-backend.com   # NO trailing /api
```

### Also Check — FastAPI Backend CORS
Ensure the FastAPI backend allows requests from your frontend domain:

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://your-frontend.com",  # Add deployed frontend URL
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## For Cloudflare Pages Deployment
Add a `_redirects` file in the `frontend/public/` folder for SPA routing:

```
/* /index.html 200
```

And set the environment variable in Cloudflare Dashboard:
```
VITE_BACKEND_URL = https://your-backend.com
```

## Quick Debug — How to Spot This Bug
Open the browser **DevTools → Network tab** while clicking any button.
Check the **Request URL** of API calls:
- ✅ Correct: `https://backend.com/api/jobs`
- ❌ Double path: `https://backend.com/api/api/jobs`

## Key Lesson
> Set `VITE_BACKEND_URL` to the **base domain only** (no `/api` at the end). The `/api` prefix belongs in the individual endpoint definitions in code, not in the environment variable.
