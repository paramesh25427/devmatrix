import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.user import User
from app.models.tenant import Tenant

client = TestClient(app)


def test_password_hashing_and_verification():
    raw_password = "SecureDevMatrixPassword2026!"
    hashed = hash_password(raw_password)
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_generation_and_decoding():
    token = create_access_token(
        user_id="usr-test-123",
        email="lead@devmatrix.local",
        role="project_lead",
        tenant_id="tenant-acme",
    )
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload["sub"] == "usr-test-123"
    assert payload["email"] == "lead@devmatrix.local"
    assert payload["role"] == "project_lead"
    assert payload["tenant_id"] == "tenant-acme"


def test_login_successful_and_unauthorized():
    # Successful login with seeded delivery manager
    res = client.post(
        "/api/auth/login",
        json={"email": "manager@devmatrix.local", "password": "DevMatrix2026!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "manager@devmatrix.local"
    assert data["user"]["role"] == "delivery_manager"

    # Failed login with invalid password
    bad_res = client.post(
        "/api/auth/login",
        json={"email": "manager@devmatrix.local", "password": "IncorrectPassword!"},
    )
    assert bad_res.status_code == 401
    assert "Invalid email or password" in bad_res.json()["detail"]


def test_get_current_user_profile():
    # Login first
    login_res = client.post(
        "/api/auth/login",
        json={"email": "manager@devmatrix.local", "password": "DevMatrix2026!"},
    )
    token = login_res.json()["access_token"]

    # Call /api/auth/me with Bearer token
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_info = me_res.json()
    assert user_info["email"] == "manager@devmatrix.local"
    assert user_info["role"] == "delivery_manager"
    assert user_info["tenant_id"] == "tenant-default"
