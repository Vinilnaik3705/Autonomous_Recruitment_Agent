import os
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.security.supabase_auth import resolve_account


@pytest.mark.skipif(os.getenv("PIPELINE_INTEGRATION") != "1", reason="requires disposable Postgres")
def test_hosted_identity_preserves_local_roles_and_rejects_email_takeover():
    from backend.database import get_db_connection
    from contextlib import closing
    subject = str(uuid4())
    email = subject + "@example.org"
    with closing(get_db_connection()) as conn:
        first = resolve_account(conn, "https://project.example", subject, email)
        assert first["role"] == "student"
        with conn, conn.cursor() as cur:
            cur.execute("UPDATE users SET role='hr' WHERE id=%s", (first["id"],))
        assert resolve_account(conn, "https://project.example", subject, email)["role"] == "hr"
        with pytest.raises(HTTPException) as blocked:
            resolve_account(conn, "https://project.example", str(uuid4()), email)
        assert blocked.value.status_code == 403
