"""
tests/conftest.py
-----------------
Shared pytest fixtures.
Uses SQLite (file-based) so tests never touch production Oracle DB.

The trick: we monkey-patch app.database.engine BEFORE importing app.main,
so the lifespan's create_all runs against SQLite, not Oracle.
"""
import os
import pytest

# ── Step 1: point the database module at SQLite BEFORE app.main is imported ─
# We set a TEST_MODE env var that database.py honours, OR we patch directly.
# The cleanest approach: patch the module-level engine object before any import.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import app.database as _db_module  # import the module (not the app yet)

TEST_DB_URL = "sqlite:///./test_loan.db"

# Replace the engine with an SQLite engine
_db_module.engine = create_engine(
    TEST_DB_URL, connect_args={"check_same_thread": False}
)

# Replace SessionLocal too
_db_module.SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=_db_module.engine
)


# ── Step 2: NOW import the app (it will use the patched engine) ──────────────
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db


def override_get_db():
    db = _db_module.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    """Create tables before each test using SQLite, drop them after."""
    Base.metadata.create_all(bind=_db_module.engine)
    yield
    Base.metadata.drop_all(bind=_db_module.engine)


@pytest.fixture(scope="function")
def client(setup_test_db):
    """
    FastAPI TestClient backed by SQLite.
    raise_server_exceptions=False returns 5xx as JSON instead of re-raising.
    """
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_customer(client) -> dict:
    """Register a default customer and return the response JSON."""
    resp = client.post(
        "/api/customers",
        json={
            "name": "Priya Raman",
            "email": "priya@example.com",
            "phone": "1234567890",
            "date_of_birth": "1990-04-15",
            "monthly_income": 45000,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
