"""Verify the hosted identity, then load the recruitment account's local role."""
from uuid import UUID

import httpx
from fastapi import HTTPException
from psycopg2.extras import RealDictCursor


async def verified_identity(token, url, key):
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            response = await client.get(url.rstrip("/") + "/auth/v1/user",
                headers={"Authorization": "Bearer " + token, "apikey": key})
        if response.status_code in (401, 403):
            raise HTTPException(401, "Invalid or expired Supabase session")
        response.raise_for_status()
        identity = response.json()
        subject = str(UUID(identity["id"]))
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(503, "Supabase Auth is unavailable") from exc
    if identity.get("is_anonymous") or not identity.get("email_confirmed_at") or not identity.get("email"):
        raise HTTPException(403, "Confirm your email before signing in")
    return subject, identity["email"].strip().lower()


def resolve_account(conn, issuer, subject, email):
    from backend.api.auth_router import ensure_users_table
    ensure_users_table(conn)
    with conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (subject,))
        cur.execute("""SELECT u.* FROM recruitment_identities i JOIN users u ON u.id=i.user_id
                       WHERE i.issuer=%s AND i.subject=%s""", (issuer, subject))
        user = cur.fetchone()
        if user:
            if user["email"].lower() != email:
                raise HTTPException(403, "Account email changed. Contact your administrator to relink.")
            return user
        cur.execute("SELECT id FROM users WHERE lower(email)=%s", (email,))
        if cur.fetchone():
            raise HTTPException(403, "An existing account requires administrator linking")
        cur.execute("""INSERT INTO users(username,email,password_hash,role,is_active)
                       VALUES (%s,%s,'oauth_only','student',true) ON CONFLICT DO NOTHING RETURNING *""",
                    (email[:12] + "-" + subject, email))
        user = cur.fetchone()
        if not user:
            raise HTTPException(409, "Account linking requires administrator review")
        cur.execute("INSERT INTO recruitment_identities(issuer,subject,user_id) VALUES (%s,%s,%s)",
                    (issuer, subject, user["id"]))
        return user
