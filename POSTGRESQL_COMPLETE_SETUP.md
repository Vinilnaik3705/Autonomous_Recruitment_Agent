# Complete PostgreSQL Setup Guide for HR Automation Platform

## Quick Start (If PostgreSQL is already installed)

### 1. Start PostgreSQL Service

```powershell
# On Windows, PostgreSQL runs as a service
# Check if it's running:
Get-Service postgresql*

# If not running, start it:
Start-Service postgresql-x64-16  # Replace 16 with your version
```

### 2. Create Database and User

```powershell
# Open Command Prompt and run:
psql -U postgres -h localhost -p 5433

# In psql prompt, execute:
CREATE DATABASE hr_db;
CREATE USER hr_user WITH PASSWORD 'hr_pass';
GRANT ALL PRIVILEGES ON DATABASE hr_db TO hr_user;
\q
```

### 3. Verify Connection

```powershell
# Test the connection with our credentials:
psql -h localhost -U hr_user -d hr_db -p 5433
# Password: hr_pass
# If successful, you'll see: hr_db=>
\q
```

### 4. Initialize Database Schema

```powershell
# From project root:
python backend/init_db_pg.py
```

### 5. Start Backend Server

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 6. Test Authentication

```powershell
curl -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"recruiter@example.com","password":"password"}'
```

---

## Fresh Installation (PostgreSQL Not Installed)

### Step 1: Download & Install PostgreSQL

1. Go to: https://www.postgresql.org/download/windows/
2. Download PostgreSQL 16 (latest stable)
3. Run installer and follow wizard:
   - **Installation Directory**: Keep default (usually C:\Program Files\PostgreSQL\16)
   - **Port**: **5433** (important - matches secrets.toml)
   - **Superuser (postgres) Password**: Set a password (you'll use this once, then use hr_pass)
   - **Locale**: Default
4. Complete installation and let it start the service

### Step 2: Configure Database

```powershell
# Open PowerShell as Administrator
# Navigate to PostgreSQL bin directory (if needed):
cd "C:\Program Files\PostgreSQL\16\bin"

# Connect as superuser:
psql -U postgres -h localhost -p 5433

# Execute these commands in psql:
CREATE DATABASE hr_db;
CREATE USER hr_user WITH PASSWORD 'hr_pass';
ALTER ROLE hr_user SET client_encoding TO 'utf8';
ALTER ROLE hr_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE hr_user SET default_transaction_deferrable TO on;
ALTER ROLE hr_user SET default_transaction_read_only TO off;
GRANT ALL PRIVILEGES ON DATABASE hr_db TO hr_user;

\q  # Exit psql
```

### Step 3: Verify Configuration

```powershell
# Test connection with new credentials:
psql -h localhost -U hr_user -d hr_db -p 5433

# Should prompt for password, enter: hr_pass
# You should see: hr_db=>

# Check users:
SELECT * FROM information_schema.tables WHERE table_catalog = 'hr_db';

\q  # Exit
```

---

## Configuration (secrets.toml)

Your `secrets.toml` should have:

```toml
[database]
host = "localhost"
name = "hr_db"
user = "hr_user"
password = "hr_pass"
port = 5433
```

---

## Troubleshooting

### "Connection refused" Error

**Cause**: PostgreSQL is not running

- Check: `Get-Service postgresql*`
- Start: `Start-Service postgresql-x64-16`
- Verify port 5433 is listening: `netstat -ano | findstr 5433`

### "FATAL: password authentication failed" Error

**Cause**: Wrong password or user doesn't exist

- Verify user and database exist via pgAdmin
- Or recreate them:
  ```sql
  DROP USER IF EXISTS hr_user;
  CREATE USER hr_user WITH PASSWORD 'hr_pass';
  GRANT ALL PRIVILEGES ON DATABASE hr_db TO hr_user;
  ```

### "database hr_db does not exist"

**Cause**: Database wasn't created

```sql
CREATE DATABASE hr_db;
GRANT ALL PRIVILEGES ON DATABASE hr_db TO hr_user;
```

---

## Using pgAdmin (GUI Alternative)

1. Open browser: http://localhost:5050
2. Default login: admin@pgadmin.org / admin
3. Add server:
   - Name: HR-Local
   - Host: localhost
   - Port: 5433
   - Username: hr_user
   - Password: hr_pass
   - DB: hr_db
4. Click "Create" database and user if needed

---

## Docker Alternative (If Docker Desktop is installed)

```powershell
# Build and start all services:
docker-compose up -d

# Verify services:
docker-compose ps

# View PostgreSQL logs:
docker-compose logs postgres

# Initialize database:
docker-compose exec fastapi python backend/init_db_pg.py

# Stop services:
docker-compose down
```

---

## Environment Variables (Optional)

If you want to override secrets.toml, set environment variables:

```powershell
$env:DB_HOST = "localhost"
$env:DB_PORT = "5433"
$env:DB_NAME = "hr_db"
$env:DB_USER = "hr_user"
$env:DB_PASSWORD = "hr_pass"
```

---

### Next Steps After Setup:

1. Run `python backend/init_db_pg.py` to initialize schema
2. Start backend: `python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000`
3. Frontend should auto-run at http://localhost:5173
4. Test login with: recruiter@example.com / password
