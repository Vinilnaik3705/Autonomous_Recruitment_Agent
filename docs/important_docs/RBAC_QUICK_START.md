# RBAC Quick Setup Guide

## What Was Implemented

A complete Role-Based Access Control (RBAC) system with 4 user roles:
- **Super Admin** - Full access to everything
- **Recruiter** - Can upload resumes, write JDs, run screening
- **Interviewer** - Read-only access to assigned candidates
- **Candidate** - Self-service portal (future)

## Quick Start (5 Steps)

### Step 1: Install Dependencies

```bash
# Backend
cd backend
pip install PyJWT

# Frontend  
cd ../frontend
npm install
```

### Step 2: Run Database Migration

```bash
psql -U postgres -d resume_analyzer -f backend/migrations/002_rbac_system.sql
```

### Step 3: Initialize Database with Demo Users

```bash
python backend/init_db.py
```

This creates demo accounts:
- **Admin:** admin@example.com / password
- **Recruiter:** recruiter@example.com / password  
- **Interviewer:** interviewer@example.com / password

### Step 4: Start Backend

```bash
cd backend
uvicorn main:app --reload
```

Backend runs at: `http://localhost:8000`

### Step 5: Start Frontend

```bash
cd frontend
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## Login with Demo Credentials

1. Open `http://localhost:5173`
2. Login page shows demo credentials
3. Try each role to see different permissions:

### Admin Experience
- Full sidebar with all navigation items
- Can upload resumes, create JDs, run screening
- Settings panel available
- Can see analytics

### Recruiter Experience  
- Screening and Interviews tabs
- Can upload resumes and run AI screening
- Cannot access admin settings
- Limited analytics view

### Interviewer Experience
- Only Interviews tab visible
- Cannot upload resumes or run screening
- Only sees assigned candidates
- Can submit interview feedback

---

## File Structure

```
backend/
  ├── auth.py (NEW) - JWT & role management
  ├── routers/
  │   └── auth_router.py (NEW) - Login/register endpoints
  ├── migrations/
  │   └── 002_rbac_system.sql (NEW) - Database schema
  ├── main.py (UPDATED) - Added auth router
  └── init_db.py (UPDATED) - Demo user creation

frontend/
  ├── src/
  │   ├── context/
  │   │   └── AuthContext.jsx (NEW) - Auth state management
  │   └── components/
  │       ├── ProtectedRoute.jsx (NEW) - Role/permission guards
  │       ├── Login.jsx (NEW) - Login page
  │       └── HRScreening.jsx (UPDATED) - Role-based UI
  └── App.jsx (UPDATED) - Auth provider wrapper
```

---

## Key Features

✅ **JWT Token Authentication**
- Secure token-based authentication
- Auto-refresh capability
- Token persistence in localStorage

✅ **Role-Based Access Control**
- 4 predefined roles with specific permissions
- Conditional UI rendering
- Backend permission validation

✅ **Protected Routes**
- Frontend protection with role/permission checks
- Automatic redirect to login if not authenticated
- Permission denied messages

✅ **Audit Logging**
- Track user actions in audit_log table
- Admin access to audit history (future)

✅ **User Management**
- Self-registration with role selection
- Admin user management (future)
- User profile display

---

## API Endpoints

### Authentication
- `POST /auth/register` - Create new account
- `POST /auth/login` - Login user
- `GET /auth/me` - Get current user info
- `POST /auth/refresh` - Refresh token

All other protected endpoints require `Authorization: Bearer {token}` header

---

## Common Tasks

### Add New User Programmatically

```python
from backend.auth import create_access_token, hash_password
from backend.database import get_db_connection

conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO users (username, email, password_hash, role, is_active) VALUES (%s, %s, %s, %s, TRUE)",
        ("john.smith", "john@example.com", hash_password("password123"), "recruiter")
    )
    conn.commit()
```

### Change User Role

```python
from backend.database import get_db_connection

conn = get_db_connection()
with conn.cursor() as cur:
    cur.execute(
        "UPDATE users SET role = %s WHERE email = %s",
        ("super_admin", "user@example.com")
    )
    conn.commit()
```

### Check User Permissions

```python
from backend.auth import get_role_permissions

permissions = get_role_permissions("recruiter")
print(permissions)  # ['upload_resumes', 'write_jd', ...]
```

---

## Troubleshooting

**Issue: "Invalid token" on login**
- Clear localStorage and try again
- Ensure backend is running
- Check SECRET_KEY in backend/auth.py

**Issue: Permissions button is disabled**
- User role doesn't have that permission
- Login as Admin or Recruiter to test
- Check hasPermission() in HRScreening.jsx

**Issue: Database connection error**
- Ensure PostgreSQL is running
- Check secrets.toml credentials
- Run migrations first

**Issue: CORS error in frontend**
- Backend CORS middleware is configured for all origins
- Ensure backend is running on localhost:8000
- Check browser console for specific error

---

## Next Steps

1. ✅ Customize roles and permissions for your organization
2. ✅ Implement candidate portal UI
3. ✅ Add audit log viewer in admin panel
4. ✅ Implement user management dashboard
5. ✅ Add email verification for registration
6. ✅ Implement password reset flow
7. ✅ Set up production SECRET_KEY
8. ✅ Enable rate limiting on auth endpoints
9. ✅ Add 2FA (two-factor authentication)
10. ✅ Implement refresh token rotation

---

## Documentation

For detailed documentation, see: `RBAC_IMPLEMENTATION_GUIDE.md`

## Support

For issues:
1. Check backend logs: `python -m uvicorn backend.main:app --reload`
2. Check frontend console: Browser DevTools → Console
3. Check PostgreSQL logs for database errors
4. Review JWT payload at jwt.io for debugging
