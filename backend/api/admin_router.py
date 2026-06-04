"""
Admin router - handles administrative tasks such as user management, role updates, and viewing system audit logs.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import List, Optional
from backend.database import get_db_connection
from psycopg2.extras import RealDictCursor
from backend.security.dependencies import require_role, get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

class UserRoleUpdate(BaseModel):
  role: str

class UserStatusUpdate(BaseModel):
  is_active: bool

class AuditLogResponse(BaseModel):
  id: int
  user_id: Optional[int]
  username: Optional[str]
  action: str
  entity_type: Optional[str]
  entity_id: Optional[str]
  ip_address: Optional[str]
  created_at: str

def create_audit_log(cur, user_id: Optional[int], action: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None, ip_address: Optional[str] = None):
  cur.execute(
    """
    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, ip_address)
    VALUES (%s, %s, %s, %s, %s)
    """,
    (user_id, action, entity_type, entity_id, ip_address)
  )

@router.get("/users", dependencies=[Depends(require_role("hr"))])
async def list_users(current_user: dict = Depends(get_current_user)):
  """List all registered users in the organization/platform."""
  conn = get_db_connection()
  try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:

      org_id = current_user.get("organization_id")
      if org_id:
        cur.execute(
          "SELECT id, username, email, role, is_active, organization_id, created_at, last_login FROM users WHERE organization_id = %s ORDER BY id DESC",
          (org_id,)
        )
      else:
        cur.execute(
          "SELECT id, username, email, role, is_active, organization_id, created_at, last_login FROM users ORDER BY id DESC"
        )
      users = cur.fetchall()
      return users
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  finally:
    conn.close()

@router.patch("/users/{user_id}/role", dependencies=[Depends(require_role("hr"))])
async def update_user_role(user_id: int, payload: UserRoleUpdate, request: Request, current_user: dict = Depends(get_current_user)):
  """Update a user's role (requires HR)."""
  valid_roles = ["hr", "recruiter", "student"]
  if payload.role not in valid_roles:
    raise HTTPException(
      status_code=400,
      detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
    )

  conn = get_db_connection()
  try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:

      cur.execute("SELECT id, username, role, organization_id FROM users WHERE id = %s", (user_id,))
      user = cur.fetchone()
      if not user:
        raise HTTPException(status_code=404, detail="User not found")

      org_id = current_user.get("organization_id")
      if org_id and user["organization_id"] != org_id:
        raise HTTPException(status_code=403, detail="Cannot manage users from other organizations")

      cur.execute(
        "UPDATE users SET role = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (payload.role, user_id)
      )

      create_audit_log(
        cur,
        current_user["user_id"],
        action=f"Updated user {user['username']} role from {user['role']} to {payload.role}",
        entity_type="user",
        entity_id=str(user_id),
        ip_address=request.client.host if request.client else None
      )

      conn.commit()
      return {"status": "success", "message": f"User role updated to {payload.role}"}
  except HTTPException:
    raise
  except Exception as e:
    conn.rollback()
    raise HTTPException(status_code=500, detail=str(e))
  finally:
    conn.close()

@router.patch("/users/{user_id}/status", dependencies=[Depends(require_role("hr"))])
async def update_user_status(user_id: int, payload: UserStatusUpdate, request: Request, current_user: dict = Depends(get_current_user)):
  """Activate or deactivate a user account."""
  conn = get_db_connection()
  try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
      cur.execute("SELECT id, username, is_active, organization_id FROM users WHERE id = %s", (user_id,))
      user = cur.fetchone()
      if not user:
        raise HTTPException(status_code=404, detail="User not found")

      if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot change your own active status")

      org_id = current_user.get("organization_id")
      if org_id and user["organization_id"] != org_id:
        raise HTTPException(status_code=403, detail="Cannot manage users from other organizations")

      cur.execute(
        "UPDATE users SET is_active = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (payload.is_active, user_id)
      )

      action_str = "activated" if payload.is_active else "deactivated"
      create_audit_log(
        cur,
        current_user["user_id"],
        action=f"User account {user['username']} was {action_str}",
        entity_type="user",
        entity_id=str(user_id),
        ip_address=request.client.host if request.client else None
      )

      conn.commit()
      return {"status": "success", "message": f"User status set to active={payload.is_active}"}
  except HTTPException:
    raise
  except Exception as e:
    conn.rollback()
    raise HTTPException(status_code=500, detail=str(e))
  finally:
    conn.close()

@router.get("/audit-logs", dependencies=[Depends(require_role("hr"))])
async def view_audit_logs(current_user: dict = Depends(get_current_user)):
  """Retrieve system audit logs (requires Super Admin)."""
  conn = get_db_connection()
  try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
      cur.execute(
        """
        SELECT a.id, a.user_id, u.username, a.action, a.entity_type, a.entity_id, a.ip_address, a.created_at
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
        LIMIT 200
        """
      )
      logs = cur.fetchall()

      formatted_logs = []
      for log in logs:
        l = dict(log)
        if l.get("created_at"):
          l["created_at"] = l["created_at"].isoformat()
        formatted_logs.append(l)

      return formatted_logs
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
  finally:
    conn.close()