"""
Shared pytest fixtures.

Uses an in-memory SQLite database so no PostgreSQL instance is needed.
The DATABASE_URL env-var is patched before anything imports app.database.
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("WATSONX_API_KEY", "")
os.environ.setdefault("WATSONX_PROJECT_ID", "")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # clean up the sqlite file
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture(scope="function")
def db():
    """Provide a DB session. Tables are shared across tests (session scope)."""
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="session")
def client():
    """A TestClient that reuses the same in-memory DB for the whole session."""
    with TestClient(app) as c:
        yield c


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_user(client, email="test@example.com", password="password123",
                  name="Test User", role="citizen"):
    resp = client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": password,
        "role": role,
    })
    return resp


def login_user(client, email="test@example.com", password="password123"):
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })
    return resp


def auth_headers(client, email="test@example.com", password="password123"):
    resp = login_user(client, email, password)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
