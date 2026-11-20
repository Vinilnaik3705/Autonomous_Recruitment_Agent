from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth import token_user_id
from backend.database import get_conn
from backend.db.queries import users

bearer = HTTPBearer(auto_error=False)
Connection = Annotated[object, Depends(get_conn)]


def get_current_user(
    conn: Connection,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    if credentials is None:
        raise HTTPException(401, "Sign in first")
    try:
        user_id = token_user_id(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(401, "Invalid or expired session") from exc
    user = users.by_id(conn, user_id)
    if not user or not user["is_active"]:
        raise HTTPException(401, "Account unavailable")
    return user


User = Annotated[dict, Depends(get_current_user)]


def staff(user: User):
    if user["role"] not in {"admin", "hr"}:
        raise HTTPException(403, "HR access required")
    return user


Staff = Annotated[dict, Depends(staff)]
