# 🚀 Complete Setup Guide - Fixed Version

## ⚠️ Current Issue

Docker Desktop is not running. PostgreSQL needs to be started in Docker.

---

## 🔧 COMPLETE STARTUP PROCEDURE (DO THIS NOW)

### **STEP 1: Start Docker Desktop** (Windows)

1. **Open Start Menu** (Press `Win` key)
2. **Type:** `Docker Desktop`
3. **Click:** "Docker Desktop.exe"
4. **Wait:** It takes 30-60 seconds to start
   - You'll see Docker icon in system tray (bottom right)
   - Wait until it says "Docker Desktop is running"

**Verify Docker is running:**

```powershell
docker ps
```

Should show columns like `CONTAINER ID IMAGE COMMAND` (even if no containers are running)

---

### **STEP 2: Start PostgreSQL Database**

Open a **NEW PowerShell terminal** and run:

```powershell
cd "C:\Users\VINIL NAIK\OneDrive\Desktop\automated_res"
docker-compose up -d postgres
```

**Wait for output:**

```
Creating hr_postgres ... done
```

**Verify it started:**

```powershell
docker ps
```

You should see:

```
CONTAINER ID   IMAGE            STATUS              PORTS
abc123def      postgres:16      Up 2 seconds        0.0.0.0:5433->5432/tcp
```

⏳ **Wait 10 seconds for database to be ready**

**Test connection:**

```powershell
docker exec hr_postgres psql -U hr_user -d hr_db -c "SELECT 1;"
```

Should show:

```
 ?column?
----------
        1
(1 row)
```

---

### **STEP 3: Restart Backend**

In the terminal running the backend:

1. **Stop it:** Press `Ctrl+C`
2. **Wait:** 3 seconds
3. **Start it again:**

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Should see:**

```
INFO:     Application startup complete.
```

---

### **STEP 4: Test the Fix**

Open another PowerShell and run:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content
```

**Success response:**

```json
{ "status": "ok", "services_ready": true, "message": "Backend is running" }
```

---

### **STEP 5: Test Frontend**

**Open browser:** http://localhost:5173

Try to:

- ✅ Register new account
- ✅ Login
- ✅ Check interview status (should show 0 interviews, but no errors!)

---

## ✅ All Steps At Once (Copy-Paste)

If you want to run all database commands together:

```powershell
# 1. Go to project directory
cd "C:\Users\VINIL NAIK\OneDrive\Desktop\automated_res"

# 2. Stop old containers (if any)
docker-compose down

# 3. Start fresh database
docker-compose up -d postgres

# 4. Wait for database to be ready
Start-Sleep -Seconds 15

# 5. Initialize database
python backend/init_db_pg.py

# 6. Check if running
docker ps
docker exec hr_postgres psql -U hr_user -d hr_db -c "SELECT COUNT(*) FROM information_schema.tables;"
```

---

## 🧪 Verification Checklist

- [ ] Docker Desktop is open and showing "running" in system tray
- [ ] `docker ps` shows postgres container
- [ ] `docker exec hr_postgres psql...` shows `1` and `(1 row)`
- [ ] Backend started successfully (see "Application startup complete")
- [ ] `http://127.0.0.1:8000/health` shows `"status":"ok"`
- [ ] Frontend loads at http://localhost:5173
- [ ] Can login without connection errors

---

## 🐛 Troubleshooting

### Problem: `docker ps` shows nothing

**Solution:** Docker is not running

```powershell
# Check Docker status
Get-Service Docker

# Start Docker (if installed)
Start-Service Docker

# OR manually open Docker Desktop application
```

### Problem: `unable to get image 'postgres:16'`

**Solution:** Docker needs internet to download the image

```powershell
# Pull the image manually
docker pull postgres:16

# Then start postgres
docker-compose up -d postgres
```

### Problem: Container is "Restarting"

**Solution:** Check logs to see what went wrong

```powershell
docker-compose logs postgres
```

### Problem: "password authentication failed"

**Solution:** Double-check secrets.toml has correct credentials

```toml
[database]
host = "localhost"
user = "hr_user"
password = "hr_pass"
port = 5433
```

### Problem: "Address already in use"

**Solution:** Stop container and restart

```powershell
docker-compose down
Start-Sleep -Seconds 5
docker-compose up -d postgres
```

---

## 🛑 Stopping Everything (When Done)

```powershell
# Stop containers (keeps data)
docker-compose down

# Stop and delete everything (wipes database)
docker-compose down -v

# Close Docker Desktop (if not needed)
# Just click the X on Docker Desktop window
```

---

## 📊 What's Different Now

### ✅ Better Offline Handling

```python
# Backend now returns mock data instead of 503 error
# Frontend can still work and development continues
{
    "total_interviews": 0,
    "status": "offline",
    "message": "Database is offline. Start with: docker-compose up -d"
}
```

### ✅ Automatic Health Check

```
GET /health
```

Perfect for monitoring! No database required.

### ✅ Response Caching

- 5-second cache prevents database spam
- Works even when database briefly goes offline
- Dramatically reduces connection errors in logs

---

## 🎯 Expected Final State

**Terminal 1 (Database):**

```
docker ps
CONTAINER ID   postgres:16   hr_postgres   Up
```

**Terminal 2 (Backend):**

```
INFO:     Application startup complete.
```

**Terminal 3 (Frontend):**

```
VITE ... ready in ... ms
Local: http://localhost:5173/
```

**Browser:**

```
Login page loads with NO connection errors ✅
```

---

## ❓ Still Having Issues?

Run diagnostic:

```powershell
Write-Host "=== SYSTEM DIAGNOSTICS ==="
Write-Host "Docker status:"
Get-Service Docker

Write-Host "`nDocker ps:"
docker ps

Write-Host "`nPostgres logs:"
docker-compose logs postgres --tail 20

Write-Host "`nDatabase test:"
docker exec hr_postgres psql -U hr_user -d hr_db -c "SELECT version();"
```

---

**Status:** ✅ Ready to Start  
**Next Action:** Start Docker Desktop, then run `docker-compose up -d postgres`
