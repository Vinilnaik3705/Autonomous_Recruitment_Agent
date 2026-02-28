"""
Auth router - handles user authentication, registration, and token management.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta
import hashlib
import httpx
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
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if user already exists
            cur.execute(
                "SELECT id FROM users WHERE email = %s OR username = %s",
                (user_data.email, user_data.username)
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
                (user_data.username, user_data.email, hashed_pwd, user_data.role)
            )
            user = cur.fetchone()
            conn.commit()
            
            # Generate token
            permissions = get_role_permissions(user_data.role)
            token = create_access_token(
                data={"username": user_data.username},
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


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login user with email and password.
    Returns JWT access token and user info.
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Query user by email
            cur.execute(
                "SELECT id, username, email, password_hash, role FROM users WHERE email = %s AND is_active = TRUE",
                (credentials.email,)
            )
            user = cur.fetchone()
            
            if not user or not verify_password(credentials.password, user["password_hash"]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
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


@router.post("/social", response_model=TokenResponse)
async def social_login(payload: dict):
    """
    Social login endpoint for Google (Real) and Apple (Mock).
    """
    provider = payload.get("provider", "google")
    role = payload.get("role", "recruiter")
    
    email = None
    username = None
    
    if provider == "google":
        token = payload.get("credential")
        if not token:
            raise HTTPException(status_code=400, detail="Google token required")
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={token}")
                if resp.status_code != 200:
                    raise HTTPException(status_code=401, detail="Invalid Google token")
                
                google_user = resp.json()
                email = google_user.get("email")
                username = google_user.get("name", email.split('@')[0])
        except HTTPException:
            raise
        except Exception as e:
            print(f"--> SOCIAL LOGIN ERROR (Google): {e}")
            raise HTTPException(status_code=500, detail=f"Google verification failed: {str(e)}")
    elif provider == "github":
        code = payload.get("credential")
        if not code:
            raise HTTPException(status_code=400, detail="GitHub code required")
        
        try:
            async with httpx.AsyncClient() as client:
                # 1. Exchange code for access token
                client_id = "Ov23liLdm7eOHKd3nbmo"
                client_secret = "204adcde7a16e72d0919e186757fe275c6c0dddd"
                
                token_resp = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": code
                    }
                )
                
                if token_resp.status_code != 200:
                    raise HTTPException(status_code=401, detail="Failed to exchange GitHub code")
                
                token_data = token_resp.json()
                gh_access_token = token_data.get("access_token")
                
                if not gh_access_token:
                    raise HTTPException(status_code=401, detail="Invalid GitHub code or secret")
                
                # 2. Fetch user profile
                user_resp = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {gh_access_token}"}
                )
                gh_user = user_resp.json()
                
                # 3. Fetch primary email
                email_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"token {gh_access_token}"}
                )
                emails = email_resp.json()
                primary_email = next((e["email"] for e in emails if e["primary"]), None)
                
                email = primary_email or gh_user.get("email")
                username = gh_user.get("login")
        except HTTPException:
            raise
        except Exception as e:
            print(f"--> SOCIAL LOGIN ERROR (GitHub): {e}")
            raise HTTPException(status_code=500, detail=f"GitHub OAuth failed: {str(e)}")
    else:
        email = payload.get("email")
        username = payload.get("username", email.split('@')[0] if email else "social_user")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for social login"
        )
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if user already exists
            cur.execute("SELECT id, username, email, role FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            if not user:
                # Create new social user
                dummy_pwd = hash_password(f"social_{email}_{provider}")
                cur.execute(
                    """
                    INSERT INTO users (username, email, password_hash, role, is_active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    RETURNING id, username, email, role
                    """,
                    (username, email, dummy_pwd, role)
                )
                user = cur.fetchone()
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
