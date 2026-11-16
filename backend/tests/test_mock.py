"""Tests for the Phase 3 mock sittings: rotation, test-order locks,
timed expiry that advances instead of blocking, ownership, writing
feedback shape, and the overall band math (see the mock contract).

The writing-feedback module (app.feedback) is owned by a parallel
build, so these tests inject a deterministic stand-in that honours the
same contract (Task 1: 5.0-6.0, Task 2: 6.0-7.0) instead of importing
whatever happens to exist on disk.
"""
from __future__ import annotations

import sys
import types
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.content import ContentStore
from app.database import get_db
from app.main import app
from app.models import MockSession, TestSession

client = TestClient(app)
BAND_LABEL = "practice estimate, not an official score"
CLOSED = "That section is closed — a mock runs in test order and you cannot go back"


@pytest.fixture()
def user_token() -> dict:
    """One fresh user per test (mirrors conftest's fixture, self-contained)."""
    email = f"test-{uuid.uuid4().hex[:12]}@prepsathi.example"
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "correct-horse-battery",
            "name": "Test Learner",
            "target_band_overall": 6.5,
            "target_band_writing": 6.0,
        },
    )
    assert resp.status_code == 201, resp.text
    return {"token": resp.json()["access_token"], "email": email}


def user_headers(fixture: dict) -> dict:
    return {"Authorization": f"Bearer {fixture['token']}"}


def _other_user_headers() -> dict:
    resp = client.post(
        "/api/auth/signup",
        json={
            "email": f"other-{uuid.uuid4().hex[:12]}@prepsathi.example",
            "password": "correct-horse-battery",
            "name": "Other",
        },
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _fake_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a deterministic analyse_writing stand-in (see module docstring)."""
    fake = types.ModuleType("app.feedback")

    def analyse_writing(prompt: dict, text: str) -> dict:
        words = len(text.split())
        low, high = (5.0, 6.0) if prompt["task"] == 1 else (6.0, 7.0)
        return {
            "prompt_id": prompt["id"],
            "word_count": words,
            "min_words": prompt["min_words"],
            "meets_minimum": words >= prompt["min_words"],
            "band_low": low,
            "band_high": high,
            "band_label": BAND_LABEL,
            "criteria": {
                name: {
                    "band_low": low,
                    "band_high": high,
                    "notes": ["Stand-in note."],
                }
                for name in (
                    "task_achievement",
                    "coherence",
                    "lexical",
                    "grammar",
                )
            },
        }

    fake.analyse_writing = analyse_writing
    monkeypatch.setitem(sys.modules, "app.feedback", fake)


def _all_correct_answers(test: dict, key: str) -> dict[str, str | int]:
    answers: dict[str, str | int] = {}
    for section in test[key]:
        for q in section["questions"]:
            if q["type"] == "mcq":
                answers[str(q["no"])] = q["answer"]
            elif q["type"] == "tfng":
                answers[str(q["no"])] = q["answer"]
            else:
                answers[str(q["no"])] = q["answers"][0]
    return answers


def _half_correct_answers(test: dict, key: str) -> dict[str, str | int]:
    answers = _all_correct_answers(test, key)
    for no in list(answers):
        if int(no) % 2 == 0:
            answers[no] = "definitely wrong on purpose"
    return answers


def _start_mock(headers: dict, track: str = "academic") -> dict:
    resp = client.post("/api/mock/start", headers=headers, json={"track": track})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _start_session(headers: dict, module: str, test_id: str) -> int:
    resp = client.post(
        f"/api/practice/{module}/{test_id}/start",
        headers=headers,
        json={"mode": "timed"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["session_id"]


def _submit_scored(
    headers: dict, mock_id: int, module: str, test_id: str, answers: dict
) -> dict:
    session_id = _start_session(headers, module, test_id)
    resp = client.post(
        f"/api/mock/{mock_id}/{module}/submit",
        headers=headers,
        json={"session_id": session_id, "answers": answers},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _backdate_test_session(session_id: int, hours: int) -> None:
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        row = db.query(TestSession).filter(TestSession.id == session_id).first()
        assert row is not None
        row.started_at = datetime.now(timezone.utc) - timedelta(hours=hours)
        db.commit()
    finally:
        db.close()


def _backdate_mock_section(mock_id: int, hours: int) -> None:
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        row = db.query(MockSession).filter(MockSession.id == mock_id).first()
        assert row is not None
        row.section_started_at = datetime.now(timezone.utc) - timedelta(hours=hours)
        db.commit()
    finally:
        db.close()


def _mock_attempts(headers: dict) -> list[dict]:
    resp = client.get("/api/attempts", headers=headers)
    assert resp.status_code == 200, resp.text
    return [a for a in resp.json() if a["kind"] == "mock"]


def _detail(headers: dict, mock_id: int) -> dict:
    resp = client.get(f"/api/mock/{mock_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _writing_text(words: int) -> str:
    return " ".join(["practice"] * words)


# -- Start / rotation ----------------------------------------------------

def test_start_academic_first_mock(user_token: dict) -> None:
    headers = user_headers(user_token)
    mock = _start_mock(headers, "academic")
    assert mock["track"] == "academic"
    assert mock["current_section"] == "listening"
    assert mock["listening_test_id"] == "L1"
    assert mock["reading_test_id"] == "RA1"
    assert mock["writing_task1_prompt_id"] == "WA-T1-01"
    assert mock["writing_task2_prompt_id"] == "WA-T2-01"
    assert mock["band_label"] == BAND_LABEL
    expires = datetime.fromisoformat(mock["section_expires_at"].replace("Z", "+00:00"))
    started = datetime.fromisoformat(mock["started_at"].replace("Z", "+00:00"))
    assert 1915 <= (expires - started).total_seconds() <= 1925


def test_start_rotation_uses_fresh_material(user_token: dict) -> None:
    headers = user_headers(user_token)
    first = _start_mock(headers, "academic")
    second = _start_mock(headers, "academic")
    third = _start_mock(headers, "academic")
    assert (first["listening_test_id"], first["reading_test_id"]) == ("L1", "RA1")
    assert (second["listening_test_id"], second["reading_test_id"]) == ("L2", "RA2")
    assert (third["listening_test_id"], third["reading_test_id"]) == ("L3", "RA3")
    assert first["writing_task1_prompt_id"] == "WA-T1-01"
    assert second["writing_task1_prompt_id"] == "WA-T1-02"
    assert third["writing_task1_prompt_id"] == "WA-T1-03"
    assert first["writing_task2_prompt_id"] == "WA-T2-01"
    assert second["writing_task2_prompt_id"] == "WA-T2-02"
    assert third["writing_task2_prompt_id"] == "WA-T2-03"


def test_start_rotation_general(user_token: dict) -> None:
    headers = user_headers(user_token)
    first = _start_mock(headers, "general")
    second = _start_mock(headers, "general")
    third = _start_mock(headers, "general")
    assert (first["listening_test_id"], first["reading_test_id"]) == ("L1", "RG1")
    assert (second["listening_test_id"], second["reading_test_id"]) == ("L2", "RG1")
    assert (third["listening_test_id"], third["reading_test_id"]) == ("L3", "RG1")
    assert first["writing_task1_prompt_id"] == "WG-T1-01"
    assert second["writing_task1_prompt_id"] == "WG-T1-02"
    assert first["writing_task2_prompt_id"] == "WG-T2-01"
    assert second["writing_task2_prompt_id"] == "WG-T2-02"


def test_mock_list_newest_first(user_token: dict) -> None:
    headers = user_headers(user_token)
    first = _start_mock(headers, "academic")
    second = _start_mock(headers, "general")
    resp = client.get("/api/mock", headers=headers)
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert [r["mock_id"] for r in rows] == [second["mock_id"], first["mock_id"]]
    assert rows[0]["track"] == "general"
    assert rows[0]["status"] == "in_progress"
    assert rows[0]["current_section"] == "listening"
    assert rows[0]["overall_band"] is None


def test_mock_requires_auth() -> None:
    assert client.get("/api/mock").status_code == 401
    assert client.post("/api/mock/start", json={"track": "academic"}).status_code == 401


def test_unknown_mock_404(user_token: dict) -> None:
    headers = user_headers(user_token)
    assert client.get("/api/mock/999999", headers=headers).status_code == 404
    resp = client.post(
        "/api/mock/999999/listening/submit",
        headers=headers,
        json={"session_id": 1, "answers": {}},
    )
    assert resp.status_code == 404


def test_wrong_user_403(user_token: dict) -> None:
    headers = user_headers(user_token)
    other = _other_user_headers()
    mock = _start_mock(headers, "academic")
    assert client.get(f"/api/mock/{mock['mock_id']}", headers=other).status_code == 403
    resp = client.post(
        f"/api/mock/{mock['mock_id']}/listening/submit",
        headers=other,
        json={"session_id": 1, "answers": {}},
    )
    assert resp.status_code == 403


# -- Full happy path -----------------------------------------------------

def test_full_happy_path_overall_band(user_token: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_feedback(monkeypatch)
    headers = user_headers(user_token)
    store = ContentStore()
    mock = _start_mock(headers, "academic")
    mock_id = mock["mock_id"]

    listening = store.listening("L1")
    assert listening is not None
    result = _submit_scored(
        headers, mock_id, "listening", "L1", _all_correct_answers(listening, "parts")
    )
    assert result["score_raw"] == 40
    assert result["band_estimate"] == 9.0
    assert result["band_label"] == BAND_LABEL
    assert result["next_section"] == "reading"
    assert result["section_expires_at"] is not None

    reading = store.reading("RA1")
    assert reading is not None
    result = _submit_scored(
        headers, mock_id, "reading", "RA1", _all_correct_answers(reading, "passages")
    )
    assert result["score_raw"] == 40
    assert result["band_estimate"] == 9.0
    assert result["next_section"] == "writing"

    resp = client.post(
        f"/api/mock/{mock_id}/writing/submit",
        headers=headers,
        json={
            "task1_text": _writing_text(180),
            "task2_text": _writing_text(300),
            "duration_seconds": 3300,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["task1"]["word_count"] == 180
    assert body["task1"]["min_words"] == 150
    assert body["task1"]["meets_minimum"] is True
    assert body["task1"]["feedback"]["prompt_id"] == "WA-T1-01"
    assert set(body["task1"]["feedback"]["criteria"]) == {
        "task_achievement",
        "coherence",
        "lexical",
        "grammar",
    }
    assert body["task2"]["word_count"] == 300
    assert body["task2"]["min_words"] == 250
    assert body["task2"]["meets_minimum"] is True
    assert body["writing_band_low"] == 5.5
    assert body["writing_band_high"] == 6.5
    assert body["next_section"] == "speaking"

    resp = client.post(
        f"/api/mock/{mock_id}/speaking/complete",
        headers=headers,
        json={"set_id": "S01", "duration_seconds": 600, "band_low": 6.0, "band_high": 7.0},
    )
    assert resp.status_code == 200, resp.text
    # overall = avg(9.0, 9.0, 6.0, 6.5) = 7.625 -> 7.5 with IELTS rounding.
    assert resp.json()["overall_band"] == 7.5
    assert resp.json()["band_label"] == BAND_LABEL
    assert resp.json()["status"] == "complete"

    detail = _detail(headers, mock_id)
    assert detail["status"] == "complete"
    assert detail["current_section"] == "done"
    assert detail["overall_band"] == 7.5
    assert detail["band_label"] == BAND_LABEL
    assert detail["sections"]["listening"] == {
        "status": "done",
        "score_raw": 40,
        "band_estimate": 9.0,
    }
    assert detail["sections"]["reading"]["status"] == "done"
    assert detail["sections"]["writing"] == {
        "status": "done",
        "band_low": 5.5,
        "band_high": 6.5,
    }
    assert detail["sections"]["speaking"] == {"status": "done", "band_estimate": 6.5}

    attempts = _mock_attempts(headers)
    assert len(attempts) == 5  # listening + reading + 2 writing + speaking
    assert {a["module"] for a in attempts} == {
        "listening",
        "reading",
        "writing",
        "speaking",
    }


def test_reading_uses_general_table(user_token: dict) -> None:
    headers = user_headers(user_token)
    store = ContentStore()
    mock = _start_mock(headers, "general")
    mock_id = mock["mock_id"]
    listening = store.listening("L1")
    assert listening is not None
    result = _submit_scored(
        headers, mock_id, "listening", "L1", _half_correct_answers(listening, "parts")
    )
    assert result["score_raw"] == 20
    assert result["band_estimate"] == 5.5
    reading = store.reading("RG1")
    assert reading is not None
    result = _submit_scored(
        headers, mock_id, "reading", "RG1", _half_correct_answers(reading, "passages")
    )
    assert result["score_raw"] == 20
    # 20/40 is 5.5 on the Academic table but 4.5 on the GT table.
    assert result["band_estimate"] == 4.5


# -- Locks, expiry, ordering ---------------------------------------------

def test_section_lock_rejects_closed_section(user_token: dict) -> None:
    headers = user_headers(user_token)
    store = ContentStore()
    mock = _start_mock(headers, "academic")
    mock_id = mock["mock_id"]
    listening = store.listening("L1")
    assert listening is not None
    _submit_scored(
        headers, mock_id, "listening", "L1", _all_correct_answers(listening, "parts")
    )
    # Listening is closed now: a second submit is rejected, and the
    # already-used TestSession cannot be replayed either.
    session_id = _start_session(headers, "listening", "L1")
    resp = client.post(
        f"/api/mock/{mock_id}/listening/submit",
        headers=headers,
        json={"session_id": session_id, "answers": {}},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == CLOSED


def test_submit_out_of_order_rejected(user_token: dict) -> None:
    headers = user_headers(user_token)
    mock = _start_mock(headers, "academic")
    session_id = _start_session(headers, "reading", "RA1")
    resp = client.post(
        f"/api/mock/{mock['mock_id']}/reading/submit",
        headers=headers,
        json={"session_id": session_id, "answers": {}},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == CLOSED


def test_expired_listening_advances_with_band_1(user_token: dict) -> None:
    headers = user_headers(user_token)
    store = ContentStore()
    mock = _start_mock(headers, "academic")
    mock_id = mock["mock_id"]
    session_id = _start_session(headers, "listening", "L1")
    _backdate_test_session(session_id, hours=2)
    listening = store.listening("L1")
    assert listening is not None
    resp = client.post(
        f"/api/mock/{mock_id}/listening/submit",
        headers=headers,
        json={
            "session_id": session_id,
            "answers": _all_correct_answers(listening, "parts"),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["score_raw"] == 0
    assert body["band_estimate"] == 1.0
    assert body["overtime"] is True
    assert body["next_section"] == "reading"
    # No Attempt is recorded for an expired section.
    assert _mock_attempts(headers) == []
    detail = _detail(headers, mock_id)
    assert detail["current_section"] == "reading"
    assert detail["sections"]["listening"]["status"] == "expired"
    assert detail["sections"]["listening"]["band_estimate"] == 1.0
    assert detail["sections"]["reading"]["status"] == "active"
    # The rest of the sitting still works.
    reading = store.reading("RA1")
    assert reading is not None
    result = _submit_scored(
        headers, mock_id, "reading", "RA1", _all_correct_answers(reading, "passages")
    )
    assert result["band_estimate"] == 9.0


def test_expired_writing_advances_without_band(
    user_token: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_feedback(monkeypatch)
    headers = user_headers(user_token)
    store = ContentStore()
    mock = _start_mock(headers, "academic")
    mock_id = mock["mock_id"]
    listening = store.listening("L1")
    reading = store.reading("RA1")
    assert listening is not None and reading is not None
    _submit_scored(
        headers, mock_id, "listening", "L1", _all_correct_answers(listening, "parts")
    )
    _submit_scored(
        headers, mock_id, "reading", "RA1", _all_correct_answers(reading, "passages")
    )
    _backdate_mock_section(mock_id, hours=2)
    resp = client.post(
        f"/api/mock/{mock_id}/writing/submit",
        headers=headers,
        json={
            "task1_text": _writing_text(180),
            "task2_text": _writing_text(300),
            "duration_seconds": 3700,
        },
    )
    assert resp.status_code == 400
    detail = _detail(headers, mock_id)
    assert detail["current_section"] == "speaking"
    assert detail["sections"]["writing"]["status"] == "expired"
    assert detail["sections"]["writing"]["band_low"] is None
    assert detail["sections"]["writing"]["band_high"] is None
    # Speaking still completes the sitting, but the overall stays null:
    # an expired writing section can never produce a band.
    resp = client.post(
        f"/api/mock/{mock_id}/speaking/complete",
        headers=headers,
        json={"set_id": "S01", "duration_seconds": 600, "band_low": 6.0, "band_high": 7.0},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["overall_band"] is None
    assert resp.json()["status"] == "in_progress"


def test_speaking_without_range_leaves_overall_null(
    user_token: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_feedback(monkeypatch)
    headers = user_headers(user_token)
    store = ContentStore()
    mock = _start_mock(headers, "academic")
    mock_id = mock["mock_id"]
    listening = store.listening("L1")
    reading = store.reading("RA1")
    assert listening is not None and reading is not None
    _submit_scored(
        headers, mock_id, "listening", "L1", _all_correct_answers(listening, "parts")
    )
    _submit_scored(
        headers, mock_id, "reading", "RA1", _all_correct_answers(reading, "passages")
    )
    resp = client.post(
        f"/api/mock/{mock_id}/writing/submit",
        headers=headers,
        json={
            "task1_text": _writing_text(180),
            "task2_text": _writing_text(300),
            "duration_seconds": 3300,
        },
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(
        f"/api/mock/{mock_id}/speaking/complete",
        headers=headers,
        json={"set_id": "S01", "duration_seconds": 600, "band_low": None, "band_high": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["overall_band"] is None
    assert resp.json()["status"] == "in_progress"
    # The speaking section stays open so it can be completed later.
    detail = _detail(headers, mock_id)
    assert detail["current_section"] == "speaking"
    assert detail["sections"]["speaking"]["status"] == "active"
    resp = client.post(
        f"/api/mock/{mock_id}/speaking/complete",
        headers=headers,
        json={"set_id": "S01", "duration_seconds": 600, "band_low": 6.0, "band_high": 7.0},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["overall_band"] == 7.5
    assert resp.json()["status"] == "complete"
