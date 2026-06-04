import os
import json
from pathlib import Path
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer
from typing import Dict, List, Optional
from backend.database import get_db_connection
from psycopg2.extras import RealDictCursor

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials as firebase_credentials
except Exception as e:
    import traceback
    print("--> FIREBASE IMPORT ERROR:", e)
    traceback.print_exc()
    firebase_admin = None
    firebase_auth = None
    firebase_credentials = None

security = HTTPBearer(auto_error=False)

# Legacy JWT settings retained for compatibility but primary auth now uses Firebase ID tokens
JWT_SECRET = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "your-internal-api-key-change-in-production")
# Keeps latest firebase init failure reason for API error details.
_firebase_init_error: Optional[str] = None

def _get_allowed_auth_emails() -> list:
    """Return allowed sign-in emails from SUPPORT_EMAIL or ALLOWED_AUTH_EMAILS env vars."""
    support_email = os.getenv("SUPPORT_EMAIL", "").strip().lower()
    allowlist = os.getenv("ALLOWED_AUTH_EMAILS", "").strip().lower()

    emails = []
    if support_email:
        emails.append(support_email)
    if allowlist:
        emails.extend([item.strip() for item in allowlist.split(",") if item.strip()])

    # Preserve order while de-duplicating
    seen = set()
    unique_emails = []
    for email in emails:
        if email and email not in seen:
            seen.add(email)
            unique_emails.append(email)
    return unique_emails


def _ensure_email_allowed(email: Optional[str]) -> None:
    """Block authentication for emails outside the configured allowlist."""
    allowed_emails = _get_allowed_auth_emails()
    normalized_email = (email or "").strip().lower()

    if not allowed_emails:
        # If no allowlist is configured, do not block sign-in.
        return

    if normalized_email not in allowed_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not allowed to access the application"
        )

def _init_firebase():
    """Initialize firebase_admin SDK using service account JSON or path from env."""
    global _firebase_init_error
    if not firebase_admin:
        _firebase_init_error = "firebase-admin package is not available"
        return False
    if firebase_admin._apps:
        _firebase_init_error = None
        return True
    svc_json = (os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or "").strip()
    svc_path_raw = (os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or "").strip().strip('"').strip("'")

    candidate_paths = []
    if svc_path_raw:
        candidate_paths.append(Path(svc_path_raw).expanduser())
    # Reliable local fallback for development when env path is missing/invalid.
    candidate_paths.extend(Path(__file__).resolve().parents[1].glob("secrets/*.json"))
    try:
        if svc_json:
            info = json.loads(svc_json)
            cred = firebase_credentials.Certificate(info)
            firebase_admin.initialize_app(cred)
            _firebase_init_error = None
            return True

        for path in candidate_paths:
            if path.exists():
                cred = firebase_credentials.Certificate(str(path))
                firebase_admin.initialize_app(cred)
                _firebase_init_error = None
                return True

        # Try default application credentials (may work in cloud deployments)
        firebase_admin.initialize_app()
        _firebase_init_error = None
        return True
    except Exception as exc:
        _firebase_init_error = str(exc)
        return False

ROLE_PERMISSIONS = {
    "hr": [
        "upload_resumes", "write_jd", "upload_jd", "run_screening",
        "view_scores", "manage_interviews", "submit_feedback",
        "view_analytics", "manage_users", "manage_settings", "view_audit_log"
    ],
    "recruiter": [
        "upload_resumes", "write_jd", "upload_jd", "run_screening",
        "view_scores", "manage_interviews", "submit_feedback", "view_analytics"
    ],
    "student": [
        "upload_resume", "check_status"
    ]
}

async def get_current_user(
    x_api_key: Optional[str] = Header(None),
    credentials=Depends(security),
    requested_role: Optional[str] = Header(None, alias="X-Requested-Role"),
) -> Dict:
    """
    Dependency to authenticate requests.
    Supports:
    1. Internal API Key validation (via X-API-Key header) for service-to-service communication.
    2. JWT validation (via Authorization Bearer token) for frontend clients.
    """

    if x_api_key and x_api_key == INTERNAL_API_KEY:
        return {
            "user_id": 0,
            "username": "system_worker",
            "email": "system@recruitment.internal",
            "role": "hr",
            "organization_id": None,
            "payload": {}
        }

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header or X-API-Key is missing"
        )

    token = credentials.credentials
    valid_roles = {"hr": "hr", "recruiter": "recruiter", "student": "student"}
    requested_role_norm = (requested_role or "").strip().lower()
    if requested_role_norm not in valid_roles:
        requested_role_norm = ""
    # Initialize Firebase SDK if available
    fb_ready = _init_firebase()
    if not fb_ready:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firebase SDK not configured on server: {_firebase_init_error or 'missing credentials'}"
        )

    try:
        payload = firebase_auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Firebase ID token: {str(e)}"
        )

    # Enforce email allowlist if configured.
    _ensure_email_allowed(payload.get("email"))

    # Firebase tokens use 'uid' as identifier
    user_id = payload.get("uid") or payload.get("sub")

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, email, role, is_active, organization_id FROM users WHERE id = %s OR email = %s",
                (user_id if str(user_id).isdigit() else -1, str(payload.get("email", "")))
            )
            user = cur.fetchone()

            if not user:
                username = payload.get("name") or payload.get("username") or payload.get("email", "").split("@")[0]
                email = payload.get("email")
                role = payload.get("role") or requested_role_norm or "recruiter"
                organization_id = payload.get("organizationId") or payload.get("organization_id")

                cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role, is_active, organization_id)
                    VALUES (%s, %s, %s, %s, TRUE, %s)
                    RETURNING id, username, email, role, is_active, organization_id
                    """,
                    (username, email, "oauth_placeholder", role, organization_id)
                )
                user = cur.fetchone()
                conn.commit()
            elif requested_role_norm and requested_role_norm in valid_roles and user.get("role") != requested_role_norm:
                # Allow updating role only when the client explicitly requests it (primarily first login after signup).
                cur.execute(
                    "UPDATE users SET role = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (requested_role_norm, user["id"]),
                )
                conn.commit()
                user["role"] = requested_role_norm

            if not user["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is deactivated"
                )

            return {
                "user_id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "organization_id": user["organization_id"],
                "payload": payload
            }
    finally:
        conn.close()

def require_role(*allowed_roles):
    """
    FastAPI dependency factory checking user roles.
    """
    def dependency(current_user: Dict = Depends(get_current_user)):
        role = current_user.get("role")
        if role not in allowed_roles and role != "hr":

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of these roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return dependency

def require_permission(permission: str):
    """
    FastAPI dependency factory checking user permissions.
    """
    def dependency(current_user: Dict = Depends(get_current_user)):
        role = current_user.get("role")
        permissions = ROLE_PERMISSIONS.get(role, [])
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' is required"
            )
        return current_user
    return dependency