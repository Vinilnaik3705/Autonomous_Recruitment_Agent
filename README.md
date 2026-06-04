# 🤖 Autonomous Recruitment Agent

An AI-powered recruitment automation system that screens resumes, matches candidates, schedules interviews, and automates onboarding.

---

## ⚡ Quick Start (5 minutes setup)

### **STEP 1: Install Docker Desktop**

- Download from: https://www.docker.com/products/docker-desktop
- Install and **start Docker Desktop** (wait 30-60 seconds)
- ✅ Verify: Open PowerShell and run `docker ps`

### **STEP 2: Clone & Setup**

```powershell
git clone <your-repo-url>
cd automated_res
```

### **STEP 3: Configure API Keys**

```powershell
Copy-Item .env.example .env
```

Open `.env` in VS Code and add:

- `OPENAI_API_KEY` = Your OpenAI key from https://platform.openai.com/api-keys
- `NEXT_PUBLIC_FIREBASE_API_KEY`, `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`, `NEXT_PUBLIC_FIREBASE_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_APP_ID`
- `FIREBASE_SERVICE_ACCOUNT_JSON` or `FIREBASE_SERVICE_ACCOUNT_PATH`
- `ALLOWED_AUTH_EMAILS` = comma-separated list of emails allowed to sign in

Everything else is pre-configured!

### **STEP 4: Start Everything**

```powershell
docker compose up -d --build
```

Wait 30-60 seconds for services to start...

### **STEP 5: Setup n8n Workflows (Private Repo)**

**Note:** n8n workflows contain proprietary business logic and are stored in a **private repository** for security.

1. Clone the private workflows repo (authorized team members only)
2. Copy workflow JSON files to n8n container or import via n8n UI
3. Workflows will use credentials from your `.env` file

### **STEP 6: Open in Browser**

- **Dashboard**: http://localhost:3000 (Frontend)
- **API Docs**: http://localhost:8000/docs (Backend)
- **Workflows**: http://localhost:5678 (n8n)

---

## 🛑 Troubleshooting

**Docker not found?**

```powershell
# Restart computer or manually start Docker Desktop
docker ps  # Should show "CONTAINER ID" header
```

**Port 8000 or 5678 already in use?**

```powershell
# Stop other services and try again
docker compose down
docker compose up -d --build
```

**Getting connection errors?**

```powershell
# Check logs
docker compose logs -f postgres    # Check database
docker compose logs -f fastapi     # Check backend
docker compose logs -f n8n         # Check workflow engine
```

---

## 📁 Project Structure

```
automated_res/
├── backend/              # FastAPI server
├── frontend/             # React web dashboard
├── workflows/            # n8n workflow exports (JSON)
├── docker-compose.yml    # Container setup
├── .env.example          # Template for configuration
└── .env                  # Your API keys (do NOT commit)
```

---

## 🚀 What You Get

✅ Resume screening with AI  
✅ Candidate ranking & matching  
✅ Automated email invitations  
✅ Interview scheduling system  
✅ Onboarding workflows  
✅ Role-based access control (RBAC)

---

## 📚 Learn More

- **n8n Workflows**: Located in the [workflows/](file:///c:/Users/VINIL NAIK/OneDrive/Desktop/Projects/automated_res/workflows) directory.

---

## 🔑 Environment Variables

**Required:**

- `OPENAI_API_KEY` - For resume analysis & candidate matching
- Firebase web config keys for frontend auth
- Firebase service account JSON/path for backend token verification
- `ALLOWED_AUTH_EMAILS` - only these email addresses can access the app

**Optional** (pre-configured):

- Database: PostgreSQL (localhost:5433)
- Backend: FastAPI (localhost:8000)
- n8n: Workflow engine (localhost:5678)
- Frontend: React app (localhost:3000)

---

## 🛑 Stop Everything

```powershell
docker compose down
```

To clean up everything (including database):

```powershell
docker compose down -v
```

---

## ❓ Need Help?

Use Docker logs and FastAPI docs for troubleshooting and API validation.
