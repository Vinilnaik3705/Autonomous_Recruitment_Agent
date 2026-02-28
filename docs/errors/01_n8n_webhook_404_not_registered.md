# Error 01: N8N Webhook "Not Registered" (404)

## Error Message
```
Proxy Error: 404: n8n Error: {"code":404,"message":"The requested webhook \"resume-upload\" is not registered"}
```

## When It Happened
When the frontend tried to upload resumes, the backend called the n8n production webhook URL but received a 404 because the workflow was not activated.

## Root Cause
N8N has **two types of webhooks**:

| Type | URL | When it works |
|---|---|---|
| **Test Webhook** | `/webhook-test/resume-upload` | Only while clicking "Test Workflow" |
| **Production Webhook** | `/webhook/resume-upload` | Only when workflow is **Active** (green toggle) |

The backend was calling the **production** URL, but the workflow was never activated — so the webhook didn't exist.

## Solution

### Step 1 — Save the Workflow
1. Open n8n at `http://localhost:5678`
2. Open your resume screening workflow
3. Press **Ctrl+S** to save

### Step 2 — Activate the Workflow
1. Look at the **top-right corner** of the workflow editor
2. Find the toggle switch
3. **Click it to turn GREEN** (Active)
4. Confirm "Workflow activated" message appears

### Step 3 — Verify
- Webhook node should show: `http://localhost:5678/webhook/resume-upload` as the Production URL
- Upload a resume from the frontend, check n8n **Executions** tab for a new run

## If Still Not Working

**Toggle keeps turning off (workflow has errors):**
1. Check all nodes for red error indicators
2. Fix errors → Save → Activate again

**Webhook still returns 404 after activation:**
1. Deactivate → Save → Reactivate
2. If still broken, restart the n8n Docker container:
   ```bash
   docker-compose restart n8n
   ```

**Nuclear option — re-import the workflow:**
1. Export workflow as JSON (`...` menu → Download)
2. Delete the workflow
3. Re-import (`+` → Import from File)
4. Save (Ctrl+S) → Activate (green toggle)

## Code Fix (Backend)
The backend webhook URL should use an environment variable so it can switch between test and production:

```python
# backend/routers/job_router.py
import os
N8N_WEBHOOK_URL = os.environ.get(
    "N8N_WEBHOOK_URL",
    "http://n8n:5678/webhook/resume-upload"  # Docker internal hostname
)
```

## Key Lesson
> Always activate workflows AFTER importing them. Imported workflows are **Inactive by default**.
