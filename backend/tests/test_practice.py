"""Tests for the Phase 2 practice API: timed tests, scoring, writing,
speaking, vocabulary review/seed, and the extended dashboard (spec
sections 3 and 5).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.content import ContentStore
from app.database import get_db
from app.main import app
from app.models import TestSession

client = TestClient(app)
BAND_LABEL = "practice estimate, not an official score"


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


def _backdate_session(session_id: int, hours: int) -> None:
    gen = app.dependency_overrides[get_db]()
    db = next(gen)
    try:
        row = db.query(TestSession).filter(TestSession.id == session_id).first()
        assert row is not None
        row.started_at = datetime.now(timezone.utc) - timedelta(hours=hours)
        db.commit()
    finally:
        db.close()


def _attempts(headers: dict) -> list[dict]:
    resp = client.get("/api/attempts", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# -- Listening ---------------------------------------------------------

def test_listening_list(user_token: dict) -> None:
    resp = client.get("/api/practice/listening", headers=user_headers(user_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 2
    assert data[0]["total_questions"] == 40
    assert data[0]["time_limit_seconds"] == 1920
    assert all(part["has_audio"] is False for test in data for part in test["parts"])


def test_listening_get_hides_answers(user_token: dict) -> None:
    resp = client.get("/api/practice/listening/L1", headers=user_headers(user_token))
    assert resp.status_code == 200, resp.text

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            assert "answer" not in obj
            assert "answers" not in obj
            assert "explanation" not in obj
            assert "evidence" not in obj
            for value in obj.values():
                _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(resp.json())


def test_listening_timed_full_marks(user_token: dict) -> None:
    headers = user_headers(user_token)
    store = ContentStore()
    test = store.listening("L1")
    assert test is not None
    start = client.post(
        "/api/practice/listening/L1/start", headers=headers, json={"mode": "timed"}
    )
    assert start.status_code == 201, start.text
    submit = client.post(
        "/api/practice/listening/L1/submit",
        headers=headers,
        json={
            "session_id": start.json()["session_id"],
            "answers": _all_correct_answers(test, "parts"),
        },
    )
    assert submit.status_code == 200, submit.text
    body = submit.json()
    assert body["score_raw"] == 40
    assert body["band_estimate"] == 9.0
    assert body["band_label"] == BAND_LABEL
    assert all(r["correct"] for r in body["results"])
    attempts = _attempts(headers)
    assert attempts[0]["module"] == "listening"
    assert attempts[0]["kind"] == "mock"
    assert attempts[0]["band_estimate"] == 9.0


def test_listening_practice_half_marks(user_token: dict) -> None:
    headers = user_headers(user_token)
    store = ContentStore()
    test = store.listening("L2")
    assert test is not None
    start = client.post(
        "/api/practice/listening/L2/start", headers=headers, json={"mode": "practice"}
    )
    assert start.status_code == 201, start.text
    assert start.json()["time_limit_seconds"] is None
    submit = client.post(
        "/api/practice/listening/L2/submit",
        headers=headers,
        json={
            "session_id": start.json()["session_id"],
            "answers": _half_correct_answers(test, "parts"),
        },
    )
    assert submit.status_code == 200, submit.text
    body = submit.json()
    assert body["score_raw"] == 20
    assert body["band_estimate"] == 5.5
    assert _attempts(headers)[0]["kind"] == "practice"


def test_listening_expired_timed_submit_records_nothing(user_token: dict) -> None:
    headers = user_headers(user_token)
    store = ContentStore()
    test = store.listening("L1")
    assert test is not None
    start = client.post(
        "/api/practice/listening/L1/start", headers=headers, json={"mode": "timed"}
    )
    session_id = start.json()["session_id"]
    _backdate_session(session_id, hours=2)
    submit = client.post(
        "/api/practice/listening/L1/submit",
        headers=headers,
        json={"session_id": session_id, "answers": _all_correct_answers(test, "parts")},
    )
    assert submit.status_code == 400, submit.text
    assert "Time expired" in submit.json()["detail"]
    assert _attempts(headers) == []


def test_double_submit_rejected(user_token: dict) -> None:
    headers = user_headers(user_token)
    store = ContentStore()
    test = store.listening("L1")
    assert test is not None
    start = client.post(
        "/api/practice/listening/L1/start", headers=headers, json={"mode": "practice"}
    )
    payload = {
        "session_id": start.json()["session_id"],
        "answers": _all_correct_answers(test, "parts"),
    }
    assert client.post("/api/practice/listening/L1/submit", headers=headers, json=payload).status_code == 200
    again = client.post("/api/practice/listening/L1/submit", headers=headers, json=payload)
    assert again.status_code == 400


def test_session_belongs_to_another_learner(user_token: dict) -> None:
    headers = user_headers(user_token)
    start = client.post(
        "/api/practice/listening/L1/start", headers=headers, json={"mode": "practice"}
    )
    assert start.status_code == 201, start.text
    # A second, different learner tries to use the session.
    other_headers = _other_user_headers()
    submit = client.post(
        "/api/practice/listening/L1/submit",
        headers=other_headers,
        json={"session_id": start.json()["session_id"], "answers": {}},
    )
    assert submit.status_code == 403


def test_unknown_test_404(user_token: dict) -> None:
    headers = user_headers(user_token)
    assert client.get("/api/practice/listening/NOPE", headers=headers).status_code == 404
    assert client.get("/api/practice/reading/NOPE", headers=headers).status_code == 404
    assert client.get("/api/practice/writing/NOPE", headers=headers).status_code == 404


# -- Reading -----------------------------------------------------------

def test_reading_lists_by_track(user_token: dict) -> None:
    headers = user_headers(user_token)
    academic = client.get("/api/practice/reading?track=academic", headers=headers)
    assert academic.status_code == 200, academic.text
    assert len(academic.json()) == 2
    general = client.get("/api/practice/reading?track=general", headers=headers)
    assert general.status_code == 200, general.text
    assert len(general.json()) == 1
    assert general.json()[0]["time_limit_seconds"] == 3600
    bad = client.get("/api/practice/reading?track=nope", headers=headers)
    assert bad.status_code == 400


def test_reading_gt_table_differs_from_academic(user_token: dict) -> None:
    """30/40 is band 7.0 on Academic but 6.0 on General Training."""
    headers = user_headers(user_token)
    store = ContentStore()
    gt = next(t for t in store.reading_tests if t["track"] == "general")
    academic = next(t for t in store.reading_tests if t["track"] == "academic")
    for test, key, expected in ((gt, "passages", 6.0), (academic, "passages", 7.0)):
        answers = _all_correct_answers(test, key)
        # Keep only the first 30 correct; the rest wrong.
        for no in list(answers):
            if int(no) > 30:
                answers[no] = "definitely wrong on purpose"
        start = client.post(
            f"/api/practice/reading/{test['id']}/start",
            headers=headers,
            json={"mode": "practice"},
        )
        assert start.status_code == 201, start.text
        submit = client.post(
            f"/api/practice/reading/{test['id']}/submit",
            headers=headers,
            json={"session_id": start.json()["session_id"], "answers": answers},
        )
        assert submit.status_code == 200, submit.text
        assert submit.json()["score_raw"] == 30
        assert submit.json()["band_estimate"] == expected


# -- Writing -----------------------------------------------------------

def test_writing_list_hides_model_answer(user_token: dict) -> None:
    headers = user_headers(user_token)
    resp = client.get("/api/practice/writing?track=academic", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 10
    assert all("model_answer" not in p for p in resp.json())
    detail = client.get("/api/practice/writing/WA-T1-01", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["model_answer"].strip() != ""
    assert detail.json()["commentary"].strip() != ""


def test_writing_submit_word_counts(user_token: dict) -> None:
    headers = user_headers(user_token)
    short = client.post(
        "/api/practice/writing/submit",
        headers=headers,
        json={"prompt_id": "WA-T1-01", "text": " ".join(["word"] * 100), "duration_seconds": 600},
    )
    assert short.status_code == 201, short.text
    assert short.json()["word_count"] == 100
    assert short.json()["min_words"] == 150
    assert short.json()["meets_minimum"] is False
    long_enough = client.post(
        "/api/practice/writing/submit",
        headers=headers,
        json={"prompt_id": "WA-T1-01", "text": " ".join(["word"] * 200), "duration_seconds": 900},
    )
    assert long_enough.json()["meets_minimum"] is True
    attempts = _attempts(headers)
    assert len(attempts) == 2
    assert attempts[0]["module"] == "writing"
    assert attempts[0]["band_estimate"] is None


# -- Speaking ----------------------------------------------------------

def test_speaking_list_and_complete(user_token: dict) -> None:
    headers = user_headers(user_token)
    resp = client.get("/api/practice/speaking", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 15
    assert resp.json()[0]["part2"]["prep_seconds"] == 60
    done = client.post(
        "/api/practice/speaking/complete",
        headers=headers,
        json={"set_id": "S01", "duration_seconds": 600},
    )
    assert done.status_code == 201, done.text
    assert _attempts(headers)[0]["module"] == "speaking"


# -- Vocabulary review + seed ------------------------------------------

def test_vocabulary_seed_is_idempotent(user_token: dict) -> None:
    headers = user_headers(user_token)
    first = client.post("/api/vocabulary/seed", headers=headers)
    assert first.status_code == 201, first.text
    assert first.json() == {"added": 200, "skipped": 0}
    second = client.post("/api/vocabulary/seed", headers=headers)
    assert second.json() == {"added": 0, "skipped": 200}


def test_vocabulary_review_intervals(user_token: dict) -> None:
    headers = user_headers(user_token)
    seed = client.post("/api/vocabulary/seed", headers=headers)
    assert seed.status_code == 201, seed.text
    due = client.get("/api/vocabulary/due", headers=headers)
    assert due.status_code == 200, due.text
    assert len(due.json()) == 50  # capped at 50 per page
    item = due.json()[0]
    correct = client.post(
        f"/api/vocabulary/{item['id']}/review", headers=headers, json={"correct": True}
    )
    assert correct.status_code == 200, correct.text
    assert correct.json()["interval_days"] == 2
    wrong = client.post(
        f"/api/vocabulary/{item['id']}/review", headers=headers, json={"correct": False}
    )
    assert wrong.json()["interval_days"] == 1
    # A correct review now moves the next review ~2 days out, so the word
    # is no longer due.
    client.post(
        f"/api/vocabulary/{item['id']}/review", headers=headers, json={"correct": True}
    )
    due_again = client.get("/api/vocabulary/due", headers=headers)
    assert all(w["id"] != item["id"] for w in due_again.json())


# -- Dashboard extension -----------------------------------------------

def test_dashboard_extension(user_token: dict) -> None:
    headers = user_headers(user_token)
    store = ContentStore()
    test = store.listening("L1")
    assert test is not None
    start = client.post(
        "/api/practice/listening/L1/start", headers=headers, json={"mode": "practice"}
    )
    client.post(
        "/api/practice/listening/L1/submit",
        headers=headers,
        json={
            "session_id": start.json()["session_id"],
            "answers": _all_correct_answers(test, "parts"),
        },
    )
    resp = client.get("/api/dashboard", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["latest_band_by_module"]["listening"] == 9.0
    assert body["latest_band_by_module"]["reading"] is None
    # Writing and Speaking have no auto band in Phase 2, so no overall.
    assert body["overall_estimate"] is None
    assert len(body["attempts_recent"]) == 1
    assert body["attempts_recent"][0]["band_label"] == BAND_LABEL
