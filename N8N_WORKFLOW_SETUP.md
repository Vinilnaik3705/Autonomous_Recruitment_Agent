# n8n Workflow Setup Guide

## System Status ✅

All containers are running successfully:

- **Backend API**: http://localhost:8000
- **n8n Platform**: http://localhost:5678
- **PostgreSQL**: port 5433

## Setup Instructions

### Step 1: Access n8n

1. Open your browser and navigate to: **http://localhost:5678**
2. If this is your first time, you may need to create an n8n account (it's local, no internet required)

### Step 2: Import the Updated Workflow

1. In n8n, click on **Workflows** in the left sidebar
2. Click the **Import** button (or the ⋮ menu → Import)
3. Select the file: `01_resume_screening_ATOMIC.json`
4. The workflow will be imported with all nodes configured

### Step 3: Configure Brevo Credential

1. In the imported workflow, find the **"Send Email via Brevo API"** node (HTTP Request node)
2. Click on the node to open its settings
3. Under **Authentication**, select **Header Auth**
4. Configure the credential:
   - **Name**: `Brevo API`
   - **Header Name**: `api-key`
   - **Header Value**: `BREVO_API_KEY_HERE`
5. Save the credential

Alternatively, you can configure it as a credential:

1. Go to **Settings** → **Credentials** in n8n
2. Click **Add Credential**
3. Search for "HTTP Header Auth" or "API"
4. Create a new credential with the Brevo API key above
5. Link it to the "Send Email via Brevo API" node

### Step 4: Verify Backend Connection

The workflow makes HTTP requests to the backend at:

- **Resume Scoring**: `http://fastapi:8000/resume/score-with-embeddings`
- **Email Generation**: `http://fastapi:8000/email/resume-shortlisted`

These URLs are already configured correctly to work within the Docker network.

### Step 5: Test the Workflow

1. In n8n, click the **Webhook** node to see the webhook URL
   - It should be something like: `http://localhost:5678/webhook/resume-upload-atomic`
2. Open the frontend at **http://localhost:5173**
3. Upload a test resume for a job posting
4. The workflow should:
   - Extract the resume text
   - Score it with AI
   - Save to database
   - Check if candidate is shortlisted (score >= 70)
   - Generate professional email
   - Send email via Brevo API

### Step 6: Monitor Execution

1. In n8n, click on **Executions** in the left sidebar
2. You'll see all workflow runs with their status (success/error)
3. Click on any execution to view the data flow through each node

## Troubleshooting

### If n8n can't reach the backend:

- Ensure all containers are running: `docker ps`
- Check backend logs: `docker logs hr_fastapi`
- Verify the URLs use `fastapi:8000` (not `localhost:8000` or `host.docker.internal:8000`)

### If emails don't send:

- Check the Brevo API key is correctly configured
- View the execution details in n8n to see the exact error
- Verify the Brevo account has email sending enabled

### If workflow execution fails:

- Check the n8n execution details for error messages
- Look at the backend logs: `docker logs hr_fastapi --tail=50`
- Ensure the test data is valid (PDF/DOCX resume, job description)

## Email Template Preview

Shortlisted candidates will receive a professional HTML email with:

- Gradient blue header with company branding
- Personalized greeting
- Next steps for the interview process
- Clear call-to-action button
- 48-hour response deadline
- Professional footer

---

## Quick Commands

**View all running containers:**

```bash
docker ps
```

**View backend logs:**

```bash
docker logs hr_fastapi --tail=50 --follow
```

**View n8n logs:**

```bash
docker logs hr_n8n --tail=50 --follow
```

**Restart all services:**

```bash
docker-compose restart
```

**Stop all services:**

```bash
docker-compose down
```

**Start all services:**

```bash
docker-compose up -d
```

---

**Your system is now ready for the company demo! 🎉**
