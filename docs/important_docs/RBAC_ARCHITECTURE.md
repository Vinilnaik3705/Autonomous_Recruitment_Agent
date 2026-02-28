# RBAC System Design Overview

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐          ┌──────────────────────────────────┐  │
│  │   Login Page    │          │    HRScreening Component         │  │
│  │  (Register)     │   ──>    │    (Role-Based UI)               │  │
│  └─────────────────┘          └──────────────────────────────────┘  │
│         │                                                           │
│         │                       ┌──────────────────────────────────┐│
│         │                       │   AuthContext (useAuth)          ││
│         │                       │  - isAuthenticated               ││
│         │                       │  - user (role, permissions)      ││
│         │                       │  - hasPermission()               ││
│         │                       │  - hasRole()                     ││
│         │                       └──────────────────────────────────┘│
│         │                                                           │
│         └──────────┬──────────────────────────────────────────────┘ │
│                    │ HTTP Bearer Token                              │
│                    ▼                                                │
├─────────────────────────────────────────────────────────────────────┤
│                         Backend (FastAPI)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │            Auth Router (/auth/*)                             │   │
│  │  - POST /register  (create user)                             │   │
│  │  - POST /login     (verify credentials, return JWT)          │   │
│  │  - GET /me         (get current user)                        │   │
│  │  - POST /refresh   (refresh token)                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                            │                                        │
│         ┌──────────────────┴──────────────────┐                     │
│         │                                      │                    │
│         ▼                                      ▼                    │
│  ┌──────────────────┐            ┌───────────────────────────┐      │
│  │   JWT Encoding   │            │  Role Validation          │      │
│  │  - user_id       │            │  - ROLE_PERMISSIONS map   │      │
│  │  - role          │            │  - @require_role()        │      │
│  │  - permissions   │            │  - @require_permission()  │      │
│  │  - exp/iat       │            │  - has_permission()       │      │
│  └──────────────────┘            └───────────────────────────┘      │
│         │                                      │                     │
│         └──────────────────┬──────────────────┘                     │
│                            │                                         │
│                            ▼                                         │
├─────────────────────────────────────────────────────────────────────┤
│                         PostgreSQL Database                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  users                    roles                 user_roles           │
│  ├─ id                    ├─ id                 ├─ user_id           │
│  ├─ username              ├─ name               ├─ role_id           │
│  ├─ email                 ├─ description        └─ assigned_at       │
│  ├─ password_hash         └─ permissions[]                           │
│  ├─ role (enum)                                                      │
│  ├─ is_active             candidate_assignments    audit_log         │
│  └─ created_at            ├─ candidate_id         ├─ user_id         │
│                           ├─ interviewer_id        ├─ action          │
│                           ├─ assigned_by           ├─ resource_type   │
│                           └─ assigned_at           ├─ resource_id     │
│                                                    ├─ timestamp       │
│                                                    └─ ...             │
└─────────────────────────────────────────────────────────────────────┘
```

## Authentication Flow

```
1. User enters credentials
   │
   └──> Frontend Login Component
        │
        └──> POST /auth/login (email, password)
             │
             ▼
2. Backend validates credentials
   │
   ├──> Hash password & compare
   │
   └──> User found & password valid?
        │
        ├─Y─> Generate JWT token + user info
        │     │
        │     └──> Return { access_token, user }
        │
        └─N──> Return 401 Unauthorized

3. Frontend stores token
   │
   └──> localStorage.setItem('auth_token', token)
        localStorage.setItem('auth_user', JSON.stringify(user))

4. Frontend updates AuthContext
   │
   └──> setUser(user)
        setToken(token)
        setIsAuthenticated(true)

5. User now authenticated
   │
   ├──> Send subsequent requests with Authorization header
   │    Authorization: Bearer {token}
   │
   └──> Backend validates JWT before processing
```

## Permission Model

```
SUPER_ADMIN
├── upload_resumes
├── write_jd
├── upload_jd
├── run_screening
├── view_scores
├── manage_interviews
├── submit_feedback
├── view_analytics
├── manage_users
├── manage_settings
└── view_audit_log

RECRUITER
├── upload_resumes
├── write_jd
├── upload_jd
├── run_screening
├── view_scores
├── manage_interviews
├── submit_feedback
└── view_analytics

INTERVIEWER
├── view_assigned_candidates
├── submit_feedback
└── view_assigned_feedback

CANDIDATE
├── upload_resume
├── check_status
└── join_interview
```

## UI Access Matrix

```
┌──────────────────────┬────────────┬───────────┬────────────┬──────────┐
│ Feature              │ Super Admin│ Recruiter │Interviewer │Candidate │
├──────────────────────┼────────────┼───────────┼────────────┼──────────┤
│ Resume Upload        │     ✅     │    ✅     │      ❌    │    Self  │
│ JD Creation          │     ✅     │    ✅     │      ❌    │     ❌   │
│ AI Screening         │     ✅     │    ✅     │      ❌    │     ❌   │
│ View All Candidates  │     ✅     │    ✅     │      ❌    │     ❌   │
│ View Assigned        │     ✅     │    ✅     │    ✅ Only │     ❌   │
│ Submit Feedback      │     ✅     │    ✅     │      ✅    │     ❌   │
│ Manage Interviews    │     ✅     │    ✅     │      ❌    │     ❌   │
│ View Analytics       │     ✅     │  Limited  │      ❌    │     ❌   │
│ Settings             │     ✅     │    ❌     │      ❌    │     ❌   │
│ User Management      │     ✅     │    ❌     │      ❌    │     ❌   │
│ Audit Logs           │     ✅     │    ❌     │      ❌    │     ❌   │
└──────────────────────┴────────────┴───────────┴────────────┴──────────┘
```

## Component Hierarchy

```
<App>
├── <AuthProvider>
│   ├── <Login />              (if not authenticated)
│   │   ├── Registration form
│   │   └── Login form
│   │
│   └── <HRScreening />        (if authenticated)
│       ├── <Sidebar />        (role-based navigation)
│       │   ├── Screening (Super/Recruiter)
│       │   ├── Interviews (All except Candidate)
│       │   ├── Dashboard (Super only)
│       │   ├── Analytics (Super/Recruiter only)
│       │   └── Settings (Super only)
│       │
│       ├── <TopBar />         (with user info + logout)
│       │
│       └── {activeTab === 'screening' && canUploadResumes && (
│           ├── <ResumUploadCard />
│           ├── <JobDescriptionCard />
│           └── <ResultsTable />
│        )}
```

## Data Flow: Role-Based UI Rendering

```
User logs in
    │
    ▼
Generate JWT { user_id: 1, role: "recruiter", permissions: [...] }
    │
    ▼
Store in AuthContext
    │
    ├─ user = { id: 1, role: "recruiter", permissions: [...] }
    ├─ token = "eyJ0eXAiOiJKV1Q..."
    ├─ isAuthenticated = true
    └─ hasPermission(perm) = check if perm in user.permissions
    └─ hasRole(role) = check if role == user.role
    │
    ▼
HRScreening Component
    │
    ├─ canUploadResumes = isSuperAdmin || isRecruiter
    ├─ canRunScreening = isSuperAdmin || isRecruiter
    ├─ canWriteJD = isSuperAdmin || isRecruiter
    │
    ├─ {!canUploadResumes && <PermissionDenied />}
    ├─ {canUploadResumes && <ScreeningTools />}
    │
    └─ <Sidebar userRole={role} .../>
       └─ {role === 'super_admin' && <AnalyticsNav />}
          {role === 'super_admin' && <SettingsNav />}
          {role === 'interviewer' && <InterviewsNav />}
```

## Token Structure

```json
JWT Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

JWT Payload:
{
  "sub": "1",                    // user_id
  "role": "recruiter",           // user role
  "exp": 1706812800,            // expiration time
  "iat": 1706726400,            // issued at time
  "username": "john.smith"       // additional claims
}

JWT Signature:
HMACSHA256(
  base64UrlEncode(header) + "." +
  base64UrlEncode(payload),
  secret_key
)
```

## Security Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Frontend (Client)                                        │
│    - Store JWT in localStorage only (NOT cookies)           │
│    - Send in Authorization: Bearer {token} header           │
│    - Don't expose token in URL                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Network                                                  │
│    - HTTPS only (in production)                             │
│    - CORS validation                                         │
│    - Token never logged                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Backend (Server)                                         │
│    - Decode & verify JWT signature                          │
│    - Check expiration time                                  │
│    - Validate role/permission middleware                    │
│    - Execute endpoint code                                  │
│    - Log action in audit_log (without sensitive data)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Database                                                 │
│    - Verify user exists & is_active = true                 │
│    - Check role in roles table                              │
│    - Verify permissions match role                          │
│    - Return data or deny access                             │
└─────────────────────────────────────────────────────────────┘
```

## Extension Points

```
ADD NEW ROLE:
1. Insert into roles table
2. Update ROLE_PERMISSIONS in backend/auth.py
3. Update role dropdown in Login.jsx
4. Update Sidebar conditionals in HRScreening.jsx

ADD NEW PERMISSION:
1. Add to ROLE_PERMISSIONS for relevant roles in backend/auth.py
2. Use @require_permission("new_perm") decorator on endpoints
3. Use hasPermission("new_perm") in frontend components

ADD NEW PROTECTED FEATURE:
1. Check permission in backend route: @require_permission("feature")
2. Check permission in frontend: useAuth().hasPermission("feature")
3. Wrap UI with <ProtectedRoute permission="feature">

ADD AUDIT LOGGING:
1. Log action in audit_log table after operation
2. Query audit_log in admin dashboard for history
3. Filter by user_id, resource_type, timestamp
```

## Deployment Considerations

1. **Production Configuration**
   - Change SECRET_KEY to secure random value
   - Set HTTPS only
   - Enable CORS restrictions
   - Add rate limiting

2. **Database**
   - Use bcrypt for password hashing (not SHA256)
   - Regular backups
   - Enable roles/row-level security (optional)

3. **Monitoring**
   - Monitor audit_log for suspicious activity
   - Alert on failed login attempts
   - Track token refresh patterns

4. **Token Management**
   - Implement refresh token rotation
   - Short-lived access tokens (15 min)
   - Long-lived refresh tokens (7 days)
   - Revocation endpoints
