import pytest
from fastapi import FastAPI, Depends, status
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timezone, timedelta
from typing import Dict
from unittest.mock import patch, MagicMock

# Import the dependencies to test
from backend.security.dependencies import (
  get_current_user,
  require_role,
  require_permission,
  JWT_SECRET,
  ALGORITHM,
  INTERNAL_API_KEY
)

# Create a test FastAPI application
test_app = FastAPI()

@test_app.get("/test-auth")
async def route_auth(current_user: dict = Depends(get_current_user)):
  return {"status": "authenticated", "user": current_user}

@test_app.get("/test-role-recruiter", dependencies=[Depends(require_role("recruiter", "hr"))])
async def route_role_recruiter(current_user: dict = Depends(get_current_user)):
  return {"status": "success", "role": current_user["role"]}

@test_app.get("/test-permission-manage-users", dependencies=[Depends(require_permission("manage_users"))])
async def route_permission_manage_users(current_user: dict = Depends(get_current_user)):
  return {"status": "success", "user": current_user["username"]}

# Create TestClient
client = TestClient(test_app)

def create_test_token(user_id: int, username: str, email: str, role: str, expires_in: int = 1) -> str:
  payload = {
    "sub": str(user_id),
    "name": username,
    "email": email,
    "role": role,
    "exp": datetime.now(timezone.utc) + timedelta(hours=expires_in)
  }
  return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

@pytest.fixture
def mock_db_connection():
  with patch("backend.security.dependencies.get_db_connection") as mock_conn:
    mock_cursor = MagicMock()
    mock_conn.return_value.cursor.return_value.__enter__.return_value = mock_cursor
    yield mock_cursor

def test_x_api_key_bypass(mock_db_connection):
  """Verify that service-to-service requests using X-API-Key bypass JWT validation."""
  response = client.get("/test-auth", headers={"X-API-Key": INTERNAL_API_KEY})
  assert response.status_code == status.HTTP_200_OK
  data = response.json()
  assert data["user"]["username"] == "system_worker"
  assert data["user"]["role"] == "hr"

def test_valid_jwt_token(mock_db_connection):
  """Verify that valid JWT session tokens are correctly parsed and authenticated."""
  token = create_test_token(user_id=10, username="alice_recruiter", email="alice@company.com", role="recruiter")
  
  # Mock DB select to return active user
  mock_db_connection.fetchone.return_value = {
    "id": 10,
    "username": "alice_recruiter",
    "email": "alice@company.com",
    "role": "recruiter",
    "is_active": True,
    "organization_id": "org_abc_123"
  }
  
  response = client.get("/test-auth", headers={"Authorization": f"Bearer {token}"})
  assert response.status_code == status.HTTP_200_OK
  data = response.json()
  assert data["user"]["user_id"] == 10
  assert data["user"]["username"] == "alice_recruiter"
  assert data["user"]["role"] == "recruiter"

def test_expired_jwt_token(mock_db_connection):
  """Verify that expired JWT tokens return an HTTP 401 Unauthorized status."""
  token = create_test_token(user_id=10, username="expired_user", email="expired@company.com", role="recruiter", expires_in=-1)
  response = client.get("/test-auth", headers={"Authorization": f"Bearer {token}"})
  assert response.status_code == status.HTTP_401_UNAUTHORIZED
  assert "expired" in response.json()["detail"].lower()

def test_rbac_role_allowed(mock_db_connection):
  """Verify allowed roles can access endpoints protected by require_role."""
  token = create_test_token(user_id=12, username="bob_hr", email="bob@company.com", role="hr")
  
  mock_db_connection.fetchone.return_value = {
    "id": 12,
    "username": "bob_hr",
    "email": "bob@company.com",
    "role": "hr",
    "is_active": True,
    "organization_id": "org_abc_123"
  }
  
  response = client.get("/test-role-recruiter", headers={"Authorization": f"Bearer {token}"})
  assert response.status_code == status.HTTP_200_OK

def test_rbac_role_denied(mock_db_connection):
  """Verify student accounts cannot access recruiter endpoints."""
  token = create_test_token(user_id=15, username="student_user", email="student@school.edu", role="student")
  
  mock_db_connection.fetchone.return_value = {
    "id": 15,
    "username": "student_user",
    "email": "student@school.edu",
    "role": "student",
    "is_active": True,
    "organization_id": "org_abc_123"
  }
  
  response = client.get("/test-role-recruiter", headers={"Authorization": f"Bearer {token}"})
  assert response.status_code == status.HTTP_403_FORBIDDEN
  assert "access denied" in response.json()["detail"].lower()

def test_rbac_permission_allowed(mock_db_connection):
  """Verify permissions are resolved correctly based on user role mapping."""
  token = create_test_token(user_id=1, username="admin_user", email="admin@company.com", role="hr")
  
  mock_db_connection.fetchone.return_value = {
    "id": 1,
    "username": "admin_user",
    "email": "admin@company.com",
    "role": "hr",
    "is_active": True,
    "organization_id": None
  }
  
  response = client.get("/test-permission-manage-users", headers={"Authorization": f"Bearer {token}"})
  assert response.status_code == status.HTTP_200_OK

def test_rbac_permission_denied(mock_db_connection):
  """Verify standard recruiters cannot access super-admin protected permissions."""
  token = create_test_token(user_id=5, username="recruiter_user", email="recruiter@company.com", role="recruiter")
  
  mock_db_connection.fetchone.return_value = {
    "id": 5,
    "username": "recruiter_user",
    "email": "recruiter@company.com",
    "role": "recruiter",
    "is_active": True,
    "organization_id": None
  }
  
  response = client.get("/test-permission-manage-users", headers={"Authorization": f"Bearer {token}"})
  assert response.status_code == status.HTTP_403_FORBIDDEN
  assert "permission denied" in response.json()["detail"].lower()
