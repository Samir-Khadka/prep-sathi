"""In-app feedback loop tests (Phase 4).

Admin access is gated by the ADMIN_EMAILS env var, read on every
request: tests set it to the fixture user's email (or clear it) and
restore it afterwards.
"""
from __future__ import annotations

import os

import pytest

from .conftest import client, user_headers

PAYLOAD = {
    "category": "bug",
    "message": "The Reading timer froze at 0:00.",
    "page": "reading",
}


@pytest.fixture(autouse=True)
def _clear_admin_emails():
    """Each test starts with no admins; tests opt in explicitly."""
    previous = os.environ.pop("ADMIN_EMAILS", None)
    yield
    if previous is None:
        os.environ.pop("ADMIN_EMAILS", None)
    else:
        os.environ["ADMIN_EMAILS"] = previous


def test_post_requires_auth() -> None:
    assert client.post("/api/feedback", json=PAYLOAD).status_code == 401


def test_post_bad_category_is_422(user_token: dict) -> None:
    resp = client.post(
        "/api/feedback",
        json={**PAYLOAD, "category": "complaint"},
        headers=user_headers(user_token),
    )
    assert resp.status_code == 422


def test_post_empty_message_is_422(user_token: dict) -> None:
    resp = client.post(
        "/api/feedback",
        json={**PAYLOAD, "message": "   "},
        headers=user_headers(user_token),
    )
    assert resp.status_code == 422


def test_post_message_too_long_is_422(user_token: dict) -> None:
    resp = client.post(
        "/api/feedback",
        json={**PAYLOAD, "message": "x" * 2001},
        headers=user_headers(user_token),
    )
    assert resp.status_code == 422


def test_valid_post_stores_and_returns(user_token: dict) -> None:
    headers = user_headers(user_token)
    resp = client.post("/api/feedback", json=PAYLOAD, headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["category"] == "bug"
    assert body["message"] == PAYLOAD["message"]
    assert body["page"] == "reading"
    assert body["resolved"] is False
    assert body["created_at"]

    # The learner can see their own past feedback, newest first.
    listed = client.get("/api/feedback", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == body["id"]


def test_admin_list_requires_admin(user_token: dict) -> None:
    headers = user_headers(user_token)
    client.post("/api/feedback", json=PAYLOAD, headers=headers)
    # No ADMIN_EMAILS set: nobody is an admin.
    assert client.get("/api/feedback/admin", headers=headers).status_code == 403


def test_admin_list_and_resolved_filter(user_token: dict) -> None:
    headers = user_headers(user_token)
    first = client.post("/api/feedback", json=PAYLOAD, headers=headers).json()
    second = client.post(
        "/api/feedback",
        json={**PAYLOAD, "category": "feature", "message": "Add dark mode."},
        headers=headers,
    ).json()

    os.environ["ADMIN_EMAILS"] = user_token["email"]
    listed = client.get("/api/feedback/admin", headers=headers)
    assert listed.status_code == 200
    # The admin list is global, so scope assertions to this test's rows
    # (the temp DB is shared across the whole test session).
    rows = [r for r in listed.json() if r["id"] in {first["id"], second["id"]}]
    assert len(rows) == 2
    # Newest first.
    assert rows[0]["id"] == second["id"]
    assert rows[1]["id"] == first["id"]

    resolved_true = client.get(
        "/api/feedback/admin?resolved=true", headers=headers
    ).json()
    assert all(r["id"] not in {first["id"], second["id"]} for r in resolved_true)
    resolved_false = client.get(
        "/api/feedback/admin?resolved=false", headers=headers
    ).json()
    assert {r["id"] for r in resolved_false} >= {first["id"], second["id"]}


def test_patch_toggles_resolved(user_token: dict) -> None:
    headers = user_headers(user_token)
    row = client.post("/api/feedback", json=PAYLOAD, headers=headers).json()

    # Non-admin cannot toggle.
    assert (
        client.patch(
            f"/api/feedback/admin/{row['id']}",
            json={"resolved": True},
            headers=headers,
        ).status_code
        == 403
    )

    os.environ["ADMIN_EMAILS"] = user_token["email"]
    resp = client.patch(
        f"/api/feedback/admin/{row['id']}",
        json={"resolved": True},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resolved"] is True

    back = client.patch(
        f"/api/feedback/admin/{row['id']}",
        json={"resolved": False},
        headers=headers,
    )
    assert back.status_code == 200
    assert back.json()["resolved"] is False

    assert (
        client.patch(
            "/api/feedback/admin/999999",
            json={"resolved": True},
            headers=headers,
        ).status_code
        == 404
    )
