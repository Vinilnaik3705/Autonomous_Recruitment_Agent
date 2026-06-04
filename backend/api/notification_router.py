from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from backend.database import get_db_connection
from backend.security.dependencies import get_current_user, require_role

router = APIRouter(prefix="/notifications", tags=["notifications"])

VALID_ROLES = ("recruiter", "hr")


class NotificationCreate(BaseModel):
    type: str = "info"
    title: str
    message: str
    user_id: Optional[int] = None
    target_role: Optional[str] = None


def _ensure_notifications_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                type VARCHAR(30) NOT NULL DEFAULT 'info',
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS user_id INTEGER")
        cur.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_read BOOLEAN")
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'notifications'
              AND column_name = 'read'
            """
        )
        if cur.fetchone():
            cur.execute('UPDATE notifications SET is_read = COALESCE(is_read, "read")')
            cur.execute('ALTER TABLE notifications DROP COLUMN "read"')
        cur.execute("UPDATE notifications SET is_read = FALSE WHERE is_read IS NULL")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)"
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_notifications_user_created
            ON notifications(user_id, created_at DESC)
            """
        )
    conn.commit()


def _normalize_type(value: str) -> str:
    normalized = (value or "info").strip().lower()
    if normalized not in ("info", "success", "alert"):
        return "info"
    return normalized


def _serialize(row: dict) -> dict:
    return {
        "id": row["id"],
        "user_id": row.get("user_id"),
        "type": row["type"],
        "title": row["title"],
        "message": row["message"],
        "read": bool(row["is_read"]),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


def _invalidate_notifications_cache(user_id: Optional[int] = None) -> None:
    from backend.database import get_redis_client

    client = get_redis_client()
    if not client:
        return
    try:
        pattern = f"cache:notifications:{user_id}:*" if user_id else "cache:notifications:*"
        for key in client.scan_iter(pattern):
            client.delete(key)
    except Exception as e:
        print(f"--> REDIS CACHE INVALIDATION ERROR: {e}")


def _resolve_recipient_user_ids(
    cur,
    payload: NotificationCreate,
    current_user: dict,
) -> List[int]:
    if payload.user_id is not None:
        cur.execute(
            "SELECT id FROM users WHERE id = %s AND is_active = TRUE",
            (payload.user_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Target user not found")
        return [int(row["id"])]

    target_role = (payload.target_role or "").strip().lower()
    if target_role in VALID_ROLES:
        cur.execute(
            "SELECT id FROM users WHERE role = %s AND is_active = TRUE",
            (target_role,),
        )
        rows = cur.fetchall() or []
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No active users found for role '{target_role}'",
            )
        return [int(r["id"]) for r in rows]

    actor_id = current_user.get("user_id")
    if actor_id and int(actor_id) > 0:
        return [int(actor_id)]

    raise HTTPException(
        status_code=400,
        detail="Provide user_id, target_role (recruiter|hr), or authenticate as a user",
    )


from fastapi import Header
from backend.security.dependencies import security

async def get_current_user_optional(
    x_api_key: Optional[str] = Header(None),
    credentials=Depends(security)
) -> Optional[dict]:
    try:
        return await get_current_user(x_api_key, credentials)
    except Exception:
        return None

@router.post("")
def create_notification(
    payload: NotificationCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Create notification(s) for one user or all users with a given role."""
    conn = None
    try:
        conn = get_db_connection()
        _ensure_notifications_table(conn)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            recipient_ids = _resolve_recipient_user_ids(cur, payload, current_user)
            created = []
            for uid in recipient_ids:
                cur.execute(
                    """
                    INSERT INTO notifications (user_id, type, title, message)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, user_id, type, title, message, is_read, created_at
                    """,
                    (
                        uid,
                        _normalize_type(payload.type),
                        payload.title,
                        payload.message,
                    ),
                )
                row = cur.fetchone()
                if row:
                    created.append(_serialize(row))
                    _invalidate_notifications_cache(uid)

            conn.commit()
            if len(created) == 1:
                return created[0]
            return {"created": len(created), "notifications": created}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.get("")
def list_notifications(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    current_user: dict = Depends(require_role("recruiter", "hr")),
):
    from backend.database import cache_get, cache_set

    user_id = int(current_user["user_id"])
    cache_key = f"cache:notifications:{user_id}:{limit}:{offset}:{unread_only}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    conn = None
    try:
        conn = get_db_connection()
        _ensure_notifications_table(conn)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            where = "WHERE user_id = %s"
            params: list = [user_id]
            if unread_only:
                where += " AND is_read = FALSE"

            cur.execute(
                f"""
                SELECT id, user_id, type, title, message, is_read, created_at
                FROM notifications
                {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (*params, limit, offset),
            )
            rows = cur.fetchall() or []

            cur.execute(
                f"SELECT COUNT(*) AS total FROM notifications {where}",
                tuple(params),
            )
            total = int(cur.fetchone()["total"])

            cur.execute(
                """
                SELECT COUNT(*) AS unread
                FROM notifications
                WHERE user_id = %s AND is_read = FALSE
                """,
                (user_id,),
            )
            unread = int(cur.fetchone()["unread"])

            result = {
                "items": [_serialize(r) for r in rows],
                "total": total,
                "unread": unread,
                "limit": limit,
                "offset": offset,
            }
            cache_set(cache_key, result, ttl=15)
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.patch("/read-all")
def mark_all_notifications_read(
    current_user: dict = Depends(require_role("recruiter", "hr")),
):
    conn = None
    try:
        user_id = int(current_user["user_id"])
        conn = get_db_connection()
        _ensure_notifications_table(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE notifications SET is_read = TRUE
                WHERE user_id = %s AND is_read = FALSE
                """,
                (user_id,),
            )
            updated = cur.rowcount
            conn.commit()
        _invalidate_notifications_cache(user_id)
        return {"updated": updated}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(require_role("recruiter", "hr")),
):
    conn = None
    try:
        user_id = int(current_user["user_id"])
        conn = get_db_connection()
        _ensure_notifications_table(conn)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE notifications
                SET is_read = TRUE
                WHERE id = %s AND user_id = %s
                RETURNING id, user_id, type, title, message, is_read, created_at
                """,
                (notification_id, user_id),
            )
            row = cur.fetchone()
            conn.commit()
            _invalidate_notifications_cache(user_id)

            if not row:
                raise HTTPException(status_code=404, detail="Notification not found")

            return _serialize(row)
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()
