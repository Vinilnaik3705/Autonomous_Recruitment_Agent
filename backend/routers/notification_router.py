from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from backend.database import get_db_connection

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationCreate(BaseModel):
    type: str = "info"
    title: str
    message: str


def _ensure_notifications_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                type VARCHAR(30) NOT NULL DEFAULT 'info',
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Backward compatibility: some existing DBs already have `read` instead of `is_read`.
        cur.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_read BOOLEAN")
        cur.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'notifications'
                      AND column_name = 'read'
                ) THEN
                    UPDATE notifications
                    SET is_read = COALESCE(is_read, "read");
                END IF;
            END $$;
            """
        )
        cur.execute("UPDATE notifications SET is_read = FALSE WHERE is_read IS NULL")
    conn.commit()


def _normalize_type(value: str) -> str:
    normalized = (value or "info").strip().lower()
    if normalized not in ("info", "success", "alert"):
        return "info"
    return normalized


def _serialize(row: dict) -> dict:
    return {
        "id": row["id"],
        "type": row["type"],
        "title": row["title"],
        "message": row["message"],
        "read": bool(row["is_read"]),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


@router.post("")
def create_notification(payload: NotificationCreate):
    conn = None
    try:
        conn = get_db_connection()
        _ensure_notifications_table(conn)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO notifications (type, title, message)
                VALUES (%s, %s, %s)
                RETURNING id, type, title, message, is_read, created_at
                """,
                (_normalize_type(payload.type), payload.title, payload.message),
            )
            row = cur.fetchone()
            conn.commit()
            return _serialize(row)
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.get("")
def list_notifications(limit: int = Query(default=100, ge=1, le=500)):
    conn = None
    try:
        conn = get_db_connection()
        _ensure_notifications_table(conn)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, type, title, message, is_read, created_at
                FROM notifications
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall() or []
            return [_serialize(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.patch("/{notification_id}/read")
def mark_notification_read(notification_id: int):
    conn = None
    try:
        conn = get_db_connection()
        _ensure_notifications_table(conn)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE notifications
                SET is_read = TRUE
                WHERE id = %s
                RETURNING id, type, title, message, is_read, created_at
                """,
                (notification_id,),
            )
            row = cur.fetchone()
            conn.commit()

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
