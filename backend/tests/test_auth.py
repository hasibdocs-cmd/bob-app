"""
Tests for /api/auth  (register, login, /me)
"""
import pytest
from tests.conftest import register_user, login_user, auth_headers


# ── Register ──────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client):
        resp = register_user(client, email="reg1@example.com")
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "reg1@example.com"
        assert data["role"] == "citizen"
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client):
        register_user(client, email="dup@example.com")
        resp = register_user(client, email="dup@example.com")
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_officer_role(self, client):
        resp = register_user(client, email="officer@example.com", role="ward_officer")
        assert resp.status_code == 201
        assert resp.json()["role"] == "ward_officer"

    def test_register_missing_email(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "No Email",
            "password": "pass123",
        })
        assert resp.status_code == 422

    def test_register_missing_name(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "noname@example.com",
            "password": "pass123",
        })
        assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    @pytest.fixture(autouse=True)
    def _ensure_user(self, client):
        register_user(client, email="login_test@example.com", password="mypassword")

    def test_login_success(self, client):
        resp = login_user(client, email="login_test@example.com", password="mypassword")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "login_test@example.com"

    def test_login_wrong_password(self, client):
        resp = login_user(client, email="login_test@example.com", password="wrong")
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = login_user(client, email="nobody@example.com", password="pass")
        assert resp.status_code == 401

    def test_login_returns_jwt(self, client):
        resp = login_user(client, email="login_test@example.com", password="mypassword")
        token = resp.json()["access_token"]
        # JWT has 3 dot-separated parts
        assert len(token.split(".")) == 3


# ── /me ───────────────────────────────────────────────────────────────────────

class TestMe:
    @pytest.fixture(autouse=True)
    def _ensure_user(self, client):
        register_user(client, email="me_test@example.com", password="pass123")

    def test_me_authenticated(self, client):
        headers = auth_headers(client, email="me_test@example.com", password="pass123")
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "me_test@example.com"

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.here"})
        assert resp.status_code == 401
