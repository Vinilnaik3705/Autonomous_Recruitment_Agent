import os
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer
from typing import Dict, List, Optional
from backend.database import get_db_connection
from psycopg2.extras import RealDictCursor

import hmac
import jwt

security = HTTPBearer(auto_error=False)
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

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
) -> Dict:
    """
    Dependency to authenticate requests.
    Supports:
    1. Internal API Key validation (via X-API-Key header) for service-to-service communication.
    2. JWT validation (via Authorization Bearer token) for frontend clients.
    """

    if INTERNAL_API_KEY and x_api_key and hmac.compare_digest(x_api_key.encode(), INTERNAL_API_KEY.encode()):
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

    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if url:
        from backend.security.supabase_auth import resolve_account, verified_identity
        subject, email = await verified_identity(credentials.credentials, url, os.environ["SUPABASE_PUBLISHABLE_KEY"])
        _ensure_email_allowed(email)
        conn = get_db_connection()
        try:
            user = resolve_account(conn, url, subject, email)
        finally:
            conn.close()
        if not user["is_active"]:
            raise HTTPException(403, "User account is deactivated")
        return {"user_id": user["id"], "username": user["username"], "email": email,
                "role": user["role"], "organization_id": user["organization_id"],
                "payload": {"sub": subject, "email": email}}

    if not JWT_SECRET:
        raise HTTPException(503, "Authentication is not configured")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM],
                             options={"require": ["sub", "exp"]})
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise HTTPException(401, "Invalid token")

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, username, email, role, is_active, organization_id FROM users WHERE id = %s",
                        (user_id,))
            user = cur.fetchone()
            if not user:
                raise HTTPException(401, "Unknown user")
            _ensure_email_allowed(user["email"])
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