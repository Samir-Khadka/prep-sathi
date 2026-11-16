"""Test setup: the API runs against an isolated temp SQLite database."""
from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# A fresh temp database per test session, so tests never touch dev data.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from app import auth as auth_helpers  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

_engine = create_engine(
    f"sqlite:///{_tmp.name}", connect_args={"check_same_thread": False}
)
_TestingSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=_engine)


def _override_get_db():
    db = _TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

client = TestClient(app)


@pytest.fixture()
def user_token() -> dict:
    """Create one fresh user per test and return their auth details."""
    import uuid

    email = f"test-{uuid.uuid4().hex[:12]}@prepsathi.example"
    password = "correct-horse-battery"
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": password,
            "name": "Test Learner",
            "target_band_overall": 6.5,
            "target_band_writing": 6.0,
        },
    )
    assert resp.status_code == 201, resp.text
    return {
        "token": resp.json()["access_token"],
        "email": email,
        "password": password,
    }


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def user_headers(fixture: dict) -> dict:
    return auth_headers(fixture["token"])
