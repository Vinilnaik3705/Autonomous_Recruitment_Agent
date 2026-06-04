"""
Auth utility wrapper mapping old calls to the new Better Auth verification layer.
"""
from backend.security.dependencies import (
    get_current_user,
    require_role,
    require_permission,
    ROLE_PERMISSIONS,
    JWT_SECRET,
    ALGORITHM
)
import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional

ACCESS_TOKEN_EXPIRE_HOURS = 24

def create_access_token(
    data: Dict,
    user_id: int,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Legacy token creator for compatibility."""
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
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

def verify_token(token: str) -> Dict:
    """Legacy token verifier for compatibility."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id = payload.get("sub") or payload.get("id") or payload.get("user_id")
        role = payload.get("role") or "recruiter"

        if user_id is None:
            raise Exception("Missing subject claim")

        return {
            "user_id": int(user_id) if str(user_id).isdigit() else user_id,
            "role": role,
            "payload": payload
        }
    except Exception as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

def get_role_permissions(role: str) -> list:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, [])