"""Dashboard, attempts, and vocabulary tests."""
from __future__ import annotations

from .conftest import client, user_headers


def test_dashboard_requires_auth() -> None:
    assert client.get("/api/dashboard").status_code == 401


def test_dashboard_starts_empty(user_token: dict) -> None:
    resp = client.get("/api/dashboard", headers=user_headers(user_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["attempts_total"] == 0
    assert body["attempts_by_module"] == {}
    assert body["vocabulary_total"] == 0
    assert body["vocabulary_due"] == 0
    assert body["target_band_overall"] == 6.5


def test_attempt_record_and_list(user_token: dict) -> None:
    headers = user_headers(user_token)
    resp = client.post(
        "/api/attempts",
        json={"module": "reading", "kind": "practice", "score_raw": 30,
              "band_estimate": 7.0, "duration_seconds": 3600},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["module"] == "reading"
    assert body["band_estimate"] == 7.0
    # Every band shown is labelled as a practice estimate, never official.
    assert body["band_label"] == "practice estimate, not an official score"

    listed = client.get("/api/attempts", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    dash = client.get("/api/dashboard", headers=headers).json()
    assert dash["attempts_total"] == 1
    assert dash["attempts_by_module"] == {"reading": 1}


def test_attempt_unknown_module_is_400(user_token: dict) -> None:
    resp = client.post(
        "/api/attempts",
        json={"module": "grammar", "kind": "practice"},
        headers=user_headers(user_token),
    )
    assert resp.status_code == 400


def test_vocabulary_add_list_delete(user_token: dict) -> None:
    headers = user_headers(user_token)
    resp = client.post(
        "/api/vocabulary",
        json={"word": "Ubiquitous", "meaning": "present everywhere", "topic": "technology"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["word"] == "ubiquitous"  # normalised to lowercase

    dup = client.post(
        "/api/vocabulary",
        json={"word": "ubiquitous", "meaning": "again", "topic": "general"},
        headers=headers,
    )
    assert dup.status_code == 409

    listed = client.get("/api/vocabulary", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    item_id = listed.json()[0]["id"]
    assert client.delete(f"/api/vocabulary/{item_id}", headers=headers).status_code == 204
    assert client.get("/api/vocabulary", headers=headers).json() == []


def test_vocabulary_requires_auth() -> None:
    assert client.get("/api/vocabulary").status_code == 401
    assert client.post("/api/vocabulary", json={"word": "x"}).status_code == 401
