import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from backend.config import get_settings


def hash_password(password, salt=None):
    salt = os.urandom(16) if salt is None else salt
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return base64.b64encode(salt + digest).decode()


def verify_password(password, encoded):
    salt = base64.b64decode(encoded)[:16]
    return hmac.compare_digest(hash_password(password, salt), encoded)


def issue_token(user_id):
    now = datetime.now(timezone.utc)
    secret = get_settings().jwt_secret
    if len(secret.encode()) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 bytes")
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=8)},
        secret,
        algorithm="HS256",
    )


def token_user_id(token):
    return int(
        jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )["sub"]
    )
