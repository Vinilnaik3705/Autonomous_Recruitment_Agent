"""
Auth utilities for JWT generation, validation, and role-based access control.
"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from functools import wraps
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()

# Role permissions mapping
ROLE_PERMISSIONS = {
    "super_admin": [
        "upload_resumes", "write_jd", "upload_jd", "run_screening",
        "view_scores", "manage_interviews", "submit_feedback",
        "view_analytics", "manage_users", "manage_settings", "view_audit_log"
    ],
    "recruiter": [
        "upload_resumes", "write_jd", "upload_jd", "run_screening",
        "view_scores", "manage_interviews", "submit_feedback", "view_analytics"
    ],
    "interviewer": [
        "view_assigned_candidates", "submit_feedback", "view_assigned_feedback"
    ],
    "candidate": [
        "upload_resume", "check_status", "join_interview"
    ]
}


def create_access_token(
    data: Dict,
    user_id: int,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with user claims.
    
    Args:
        data: Additional claims to include
        user_id: User ID to embed in token
        role: User role to embed in token
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        
        if user_id is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        
        return {
            "user_id": int(user_id),
            "role": role,
            "payload": payload
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(authorization: str = Depends(HTTPBearer())) -> Dict:
    """
    Dependency to extract and validate current user from Bearer token.
    
    Returns:
        Dict with user_id, role, and full payload
    """
    token = authorization.credentials
    return verify_token(token)


def require_role(*allowed_roles):
    """
    Decorator to enforce role-based access control.
    
    Usage:
        @app.get("/admin-only")
        @require_role("super_admin")
        async def admin_endpoint(current_user: Dict = Depends(get_current_user)):
            ...
            
        @app.get("/recruiter-or-admin")
        @require_role("recruiter", "super_admin")
        async def recruiter_endpoint(current_user: Dict = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: Dict = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized"
                )
            
            if current_user["role"] not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def require_permission(permission: str):
    """
    Decorator to enforce permission-based access control.
    
    Usage:
        @app.post("/upload-resumes")
        @require_permission("upload_resumes")
        async def upload_resumes(current_user: Dict = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: Dict = None, **kwargs):
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized"
                )
            
            user_role = current_user["role"]
            user_permissions = ROLE_PERMISSIONS.get(user_role, [])
            
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        
        return wrapper
    return decorator


def has_permission(role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.
    
    Args:
        role: User role
        permission: Permission to check
        
    Returns:
        True if role has permission, False otherwise
    """
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions


def get_role_permissions(role: str) -> List[str]:
    """
    Get all permissions for a role.
    
    Args:
        role: User role
        
    Returns:
        List of permissions
    """
    return ROLE_PERMISSIONS.get(role, [])
