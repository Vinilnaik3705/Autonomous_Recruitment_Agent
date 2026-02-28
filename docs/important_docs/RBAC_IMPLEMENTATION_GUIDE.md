# RBAC System Implementation Guide

## Overview

A complete Role-Based Access Control (RBAC) system has been implemented for the HR Automation Platform. This system manages user authentication, authorization, and permissions across the entire application.

## Architecture

### Backend Components

1. **Auth Utilities** (`backend/auth.py`)
   - JWT token generation and validation
   - Role-based access control decorators
   - Permission management system
   - Secure password hashing

2. **Auth Router** (`backend/routers/auth_router.py`)
   - `POST /auth/register` - Register new users
   - `POST /auth/login` - Login with email/password
   - `GET /auth/me` - Get current user info
   - `POST /auth/refresh` - Refresh access token

3. **Database Schema** (`backend/migrations/002_rbac_system.sql`)
   - Users table with role column
   - Roles table with permissions
   - User-roles junction table
   - Candidate assignments (interviewer → candidates)
   - Audit log for activity tracking

### Frontend Components

1. **Auth Context** (`frontend/src/context/AuthContext.jsx`)
   - Global authentication state management
   - Login/register/logout functions
   - Role and permission checking utilities
   - Token persistence and refresh

2. **Protected Route Components** (`frontend/src/components/ProtectedRoute.jsx`)
   - `<ProtectedRoute>` - Conditional rendering based on role/permissions
   - `<ShowIfRole>` - Show component only for specific role
   - `<ShowIfPermission>` - Show component only if user has permission
   - Various conditional display components

3. **Login Component** (`frontend/src/components/Login.jsx`)
   - User registration and login interface
   - Role selection for new accounts
   - Demo credentials display

4. **Updated HRScreening** (`frontend/src/components/HRScreening.jsx`)
   - Sidebar navigation based on role
   - Permission checks for all features
   - User info display in top bar with logout

## User Roles & Permissions

### 1. Super Admin
- **Access Level:** Full system access
- **Permissions:**
  - Upload resumes
  - Write/upload/generate job descriptions
  - Run AI screening
  - View candidate scores
  - Manage interviews
  - Submit feedback
  - View analytics
  - Manage users
  - Configure settings
  - View audit logs

- **UI Features:**
  - All sidebar navigation items visible
  - Settings/Admin panel available
  - Analytics dashboard visible
  - No restrictions on any features

### 2. Recruiter
- **Access Level:** Core HR functions
- **Permissions:**
  - Upload resumes
  - Write/upload/generate job descriptions
  - Run AI screening
  - View candidate scores
  - Manage interviews
  - Submit feedback
  - View analytics (limited)

- **UI Features:**
  - Screening and Interviews tabs visible
  - Can create and manage JDs
  - Can run screening workflows
  - No access to settings or user management

### 3. Interviewer
- **Access Level:** Read-only + feedback
- **Permissions:**
  - View assigned candidates only
  - Submit feedback
  - View assigned feedback

- **UI Features:**
  - Only Interviews tab visible
  - Cannot access screening tools
  - Only sees candidates assigned to them
  - Can submit interview scores/feedback

### 4. Candidate (Future)
- **Access Level:** Self-service portal
- **Permissions:**
  - Upload own resume
  - Check application status
  - Join interview links

- **UI Features:**
  - Separate candidate portal
  - Cannot see other candidates
  - Limited to their own application

## Database Setup

### 1. Create RBAC Tables
Run the migration file to create necessary tables:

```bash
# From project root
psql -U postgres -d resume_analyzer -f backend/migrations/002_rbac_system.sql
```

### 2. Initialize Database with Demo Users

```python
from backend.init_db import init_db
init_db()
```

This creates:
- Roles table with 4 core roles
- Demo users for testing:
  - Admin: admin@example.com / password (super_admin role)
  - Recruiter: recruiter@example.com / password (recruiter role)
  - Interviewer: interviewer@example.com / password (interviewer role)

## API Authentication

### 1. Register New User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john.doe",
    "email": "john@example.com",
    "password": "secure_password",
    "role": "recruiter"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "john.doe",
    "email": "john@example.com",
    "role": "recruiter",
    "permissions": ["upload_resumes", "write_jd", ...]
  }
}
```

### 2. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "secure_password"
  }'
```

### 3. Use JWT Token in Requests

All authenticated endpoints require the Bearer token:

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

## Frontend Usage

### 1. Wrap App with AuthProvider

In `frontend/src/App.jsx`:

```jsx
import { AuthProvider } from './context/AuthContext'

function App() {
  return (
    <AuthProvider>
      <YourAppComponent />
    </AuthProvider>
  )
}
```

### 2. Use Auth Hook in Components

```jsx
import { useAuth } from '../context/AuthContext'

function MyComponent() {
  const auth = useAuth()
  
  // Check authentication
  if (!auth.isAuthenticated) {
    return <p>Please log in</p>
  }
  
  // Check role
  if (auth.hasRole('recruiter')) {
    // Show recruiter features
  }
  
  // Check permission
  if (auth.hasPermission('upload_resumes')) {
    // Show upload button
  }
  
  return <div>Hello {auth.user.username}</div>
}
```

### 3. Protected Routes

```jsx
import { ProtectedRoute, ShowIfRole } from './components/ProtectedRoute'

function App() {
  return (
    <>
      {/* Require specific role */}
      <ProtectedRoute role="recruiter">
        <ResumeUpload />
      </ProtectedRoute>
      
      {/* Require multiple roles (OR logic) */}
      <ProtectedRoute role={["recruiter", "super_admin"]}>
        <ScreeningTools />
      </ProtectedRoute>
      
      {/* Require permission */}
      <ProtectedRoute permission="upload_resumes">
        <UploadButton />
      </ProtectedRoute>
      
      {/* Require all permissions (AND logic) */}
      <ProtectedRoute permissions={["upload_resumes", "run_screening"]} all>
        <FullScreeningWorkflow />
      </ProtectedRoute>
      
      {/* Show only for specific role */}
      <ShowIfRole role="super_admin">
        <AdminPanel />
      </ShowIfRole>
    </>
  )
}
```

## Configuration

### Environment Variables

Add to `.env` or `secrets.toml`:

```toml
[auth]
SECRET_KEY = "your-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRE_HOURS = 24
ALGORITHM = "HS256"
```

### Token Expiration

Default: 24 hours (configurable in `backend/auth.py`)

```python
ACCESS_TOKEN_EXPIRE_HOURS = 24
```

## Security Best Practices

1. **Never trust frontend validation alone** - Always validate roles/permissions on the backend
2. **Use HTTPS in production** - JWT tokens should only be transmitted over HTTPS
3. **Rotate secret keys regularly** - Change `SECRET_KEY` periodically
4. **Hash passwords securely** - Uses SHA256 (upgrade to bcrypt in production)
5. **Implement rate limiting** - Prevent brute force attacks on auth endpoints
6. **Audit logging** - Track all sensitive operations in audit_log table
7. **Disable expired sessions** - Implement automatic logout after inactivity

## Running the Application

### 1. Install Dependencies

Backend:
```bash
pip install PyJWT fastapi uvicorn
```

Frontend:
```bash
npm install
```

### 2. Start Backend

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`

### 3. Start Frontend

```bash
npm run dev
```

The UI will be available at `http://localhost:5173`

### 4. Test with Demo Credentials

Login page will show demo credentials:
- Admin: admin@example.com / password
- Recruiter: recruiter@example.com / password
- Interviewer: interviewer@example.com / password

## Extending the System

### Add New Role

1. Insert into `roles` table:
```sql
INSERT INTO roles (name, description, permissions) 
VALUES ('new_role', 'Description', ARRAY['permission1', 'permission2']);
```

2. Update permission map in `backend/auth.py`:
```python
ROLE_PERMISSIONS = {
    'new_role': ['permission1', 'permission2', ...]
}
```

### Add New Permission

1. Define in `backend/auth.py` ROLE_PERMISSIONS map
2. Use in decorators:
```python
@app.post("/protected-endpoint")
@require_permission("new_permission")
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    pass
```

### Implement Candidate Portal

Create new component with `role="candidate"` access
Modify `HRScreening.jsx` to render candidate interface based on role

## Troubleshooting

### Token Expired Error
- User needs to login again or token needs refresh
- Check `ACCESS_TOKEN_EXPIRE_HOURS` setting

### Permission Denied Error
- User's role doesn't have required permission
- Check role assignments in database

### Invalid Token Error
- Token might be malformed or corrupted
- Clear localStorage and login again
- Verify `SECRET_KEY` matches between frontend and backend

### CORS Issues
- Ensure CORS middleware is properly configured
- Backend: Check `allow_origins` in CORSMiddleware

## Support

For issues or questions:
1. Check auth logs in `audit_log` table
2. Review JWT token claims (use jwt.io for debugging)
3. Check database role/permission configuration
