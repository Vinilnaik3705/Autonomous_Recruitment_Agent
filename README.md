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
3. Workflows will use credentials from your `secrets.toml`

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
automated_res/ (Public Repository)
├── backend/              # FastAPI server
├── frontend/             # React web dashboard
├── docker-compose.yml    # Container setup
├── .env.example          # Template for configuration
└── secrets.toml          # Your API keys (do NOT commit)

automation-workflows/ (Private Repository - Authorized Team Only)
├── *.json                # n8n workflow exports (confidential)
└── setup-guide/          # Instructions for importing workflows
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

- **n8n Workflows**: Available in private `automation-workflows` repository (authorized team members only)

---

## 🔑 Environment Variables

**Required:**
- `OPENAI_API_KEY` - For resume analysis & candidate matching

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
