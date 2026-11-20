from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from backend.auth import issue_token, hash_password, verify_password
from backend.db.queries import users
from backend.security.dependencies import Connection, User

router = APIRouter(prefix="/auth")


class Credentials(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]


class Registration(Credentials):
    full_name: Annotated[str, Field(min_length=1, max_length=200)]


class Session(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=201, response_model=Session)
def register(body: Registration, conn: Connection):
    user = users.create(
        conn, body.email.lower(), body.full_name.strip(), hash_password(body.password)
    )
    if not user:
        raise HTTPException(409, "Account already exists")
    return Session(access_token=issue_token(user["id"]))


@router.post("/login", response_model=Session)
def login(body: Credentials, conn: Connection):
    user = users.by_email(conn, body.email.lower())
    if (
        not user
        or not user["is_active"]
        or not verify_password(body.password, user["password_hash"])
    ):
        raise HTTPException(401, "Invalid email or password")
    return Session(access_token=issue_token(user["id"]))


@router.get("/me")
def me(user: User):
    return user
