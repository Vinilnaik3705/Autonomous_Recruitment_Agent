"""
Auth router - handles user authentication, registration, and token management.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta
import hashlib
import re
import requests
from psycopg2.extras import RealDictCursor
from backend.database import get_db_connection
from backend.auth import (
    create_access_token, verify_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_HOURS, get_role_permissions
)

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Pydantic Models ---
class UserRegister(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "recruiter"  # Default role


class UserLogin(BaseModel):
    email: str
    password: str


class SocialAuthRequest(BaseModel):
    credential: str
    provider: str
    role: Optional[str] = "recruiter"
    mode: Optional[str] = "login"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    permissions: list


def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def ensure_users_table(conn) -> None:
    """Ensure the users table and required columns exist."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'recruiter',
                workspace_id INTEGER,
                department VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Add missing columns safely if table existed before RBAC migration
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'recruiter'")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS workspace_id INTEGER")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100)")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    conn.commit()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return hash_password(plain_password) == hashed_password


def _sanitize_username(seed: str) -> str:
    raw = (seed or "user").strip().lower()
    raw = re.sub(r"[^a-z0-9._-]", "", raw)
    return raw[:30] or "user"


def _build_unique_username(cur, preferred: str) -> str:
    base = _sanitize_username(preferred)
    candidate = base
    suffix = 1
    while True:
        cur.execute("SELECT 1 FROM users WHERE username = %s", (candidate,))
        if not cur.fetchone():
            return candidate
        candidate = f"{base}{suffix}"
        suffix += 1


def _fetch_google_profile(access_token: str) -> dict:
    try:
        response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except requests.RequestException:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach Google OAuth services",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )

    profile = response.json()
    if not profile.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is unavailable",
        )
    return profile


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """
    Register a new user and return access token.
    
    Default roles:
    - super_admin: Only for initial setup/admin users
    - recruiter: Standard user (default)
    - interviewer: Interviewer accounts
    - candidate: Candidate portal accounts
    """
    conn = None
    try:
        normalized_email = (user_data.email or "").strip().lower()
        normalized_username = (user_data.username or "").strip()
        if not normalized_email or not normalized_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username and email are required",
            )

        conn = get_db_connection()
        ensure_users_table(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if user already exists
            cur.execute(
                "SELECT id FROM users WHERE LOWER(email) = LOWER(%s) OR username = %s",
                (normalized_email, normalized_username)
            )
            if cur.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already exists"
                )
            
            # Validate role
            valid_roles = ["super_admin", "recruiter", "interviewer", "candidate"]
            if user_data.role not in valid_roles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                )
            
            # Create new user
            hashed_pwd = hash_password(user_data.password)
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING id, username, email, role
                """,
                (normalized_username, normalized_email, hashed_pwd, user_data.role)
            )
            user = cur.fetchone()
            conn.commit()
            
            # Generate token
            permissions = get_role_permissions(user_data.role)
            token = create_access_token(
                data={"username": user["username"]},
                user_id=user["id"],
                role=user_data.role,
                expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
            )
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": user["role"],
                    "permissions": permissions
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if conn:
            conn.close()


@router.post("/social", response_model=TokenResponse)
async def social_auth(payload: SocialAuthRequest):
    """
    Social authentication endpoint.
    Currently supports Google access tokens from the frontend OAuth flow.
    """
    provider = (payload.provider or "").strip().lower()
    credential = (payload.credential or "").strip()
    auth_mode = (payload.mode or "login").strip().lower()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing social credential",
        )

    if provider == "github":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub social login is not configured on backend",
        )
    if provider != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported social provider",
        )
    if auth_mode not in {"login", "signup"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid social auth mode. Use 'login' or 'signup'",
        )

    profile = _fetch_google_profile(credential)
    email = profile.get("email", "").strip().lower()
    display_name = profile.get("name") or email.split("@")[0]

    conn = None
    try:
        conn = get_db_connection()
        ensure_users_table(conn)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, email, role FROM users WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()

            if auth_mode == "login":
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="No account found for this Google email. Please sign up first",
                    )
            else:
                if user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Account already exists. Please sign in instead",
                    )

                valid_roles = ["super_admin", "recruiter", "interviewer", "candidate"]
                requested_role = payload.role if payload.role in valid_roles else "recruiter"

                preferred_username = _sanitize_username(email.split("@")[0] or display_name)
                username = _build_unique_username(cur, preferred_username)

                # Keep schema compatibility: users.password_hash is NOT NULL.
                synthetic_password_hash = hash_password(f"social::{provider}::{email}")

                cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role, is_active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    RETURNING id, username, email, role
                    """,
                    (username, email, synthetic_password_hash, requested_role),
                )
                user = cur.fetchone()

            cur.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (user["id"],),
            )
            conn.commit()

            permissions = get_role_permissions(user["role"])
            token = create_access_token(
                data={"username": user["username"]},
                user_id=user["id"],
                role=user["role"],
                expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
            )

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": user["role"],
                    "permissions": permissions,
                },
            }
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    finally:
        if conn:
            conn.close()


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login user with email and password.
    Returns JWT access token and user info.
    """
    conn = None
    try:
        identifier = (credentials.email or "").strip()
        if not identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required",
            )

        conn = get_db_connection()
        ensure_users_table(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Query user by email (case-insensitive) and allow username as fallback.
            cur.execute(
                """
                SELECT id, username, email, password_hash, role
                FROM users
                WHERE (LOWER(email) = LOWER(%s) OR username = %s)
                  AND is_active = TRUE
                """,
                (identifier, identifier)
            )
            user = cur.fetchone()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No account found for this email. Please sign up first"
                )

            if not verify_password(credentials.password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid password"
                )
            
            # Update last_login
            cur.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (user["id"],)
            )
            conn.commit()
            
            # Generate token
            permissions = get_role_permissions(user["role"])
            token = create_access_token(
                data={"username": user["username"]},
                user_id=user["id"],
                role=user["role"],
                expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
            )
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "role": user["role"],
                    "permissions": permissions
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if conn:
            conn.close()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user's info.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, email, role FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            permissions = get_role_permissions(user["role"])
            
            return {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "permissions": permissions
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if conn:
            conn.close()


@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """
    Refresh an access token.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT username, role FROM users WHERE id = %s",
                (current_user["user_id"],)
            )
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Create new token
            token = create_access_token(
                data={"username": user["username"]},
                user_id=current_user["user_id"],
                role=user["role"],
                expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
            )
            
            permissions = get_role_permissions(user["role"])
            
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": current_user["user_id"],
                    "username": user["username"],
                    "email": current_user["payload"].get("email", ""),
                    "role": user["role"],
                    "permissions": permissions
                }
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        if conn:
            conn.close()