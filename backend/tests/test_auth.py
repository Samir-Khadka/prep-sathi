"""Auth tests: signup, duplicate signup, login, and /me."""
from __future__ import annotations

from .conftest import auth_headers, client, user_headers


def test_signup_then_me(user_token: dict) -> None:
    resp = client.get("/api/auth/me", headers=user_headers(user_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == user_token["email"]
    assert body["name"] == "Test Learner"
    assert body["target_band_overall"] == 6.5
    assert body["target_band_writing"] == 6.0
    assert "password_hash" not in body


def test_duplicate_signup_is_409(user_token: dict) -> None:
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": user_token["email"],
            "password": "another-password-1",
            "name": "Copy",
        },
    )
    assert resp.status_code == 409


def test_signup_rejects_short_password() -> None:
    resp = client.post(
        "/api/auth/signup",
        json={"email": "short@prepsathi.example", "password": "abc", "name": "X"},
    )
    assert resp.status_code == 422


def test_login_wrong_password_is_401(user_token: dict) -> None:
    resp = client.post(
        "/api/auth/login",
        json={"email": user_token["email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401


def test_login_unknown_email_is_401() -> None:
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@prepsathi.example", "password": "whatever-123"},
    )
    assert resp.status_code == 401


def test_me_without_token_is_401() -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_bad_token_is_401() -> None:
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert resp.status_code == 401


def test_login_returns_working_token(user_token: dict) -> None:
    resp = client.post(
        "/api/auth/login",
        json={"email": user_token["email"], "password": user_token["password"]},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    assert client.get("/api/auth/me", headers=auth_headers(token)).status_code == 200
