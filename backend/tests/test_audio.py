"""Listening audio pipeline tests (Phase 5.2).

Serving: 200 full file, 206 partial ranges, 404 missing, 400 bad ids.
Upload: 403 non-admin, 400 bad files, 200 success flips the content
``audio_url`` and the file is served afterwards — no restart.

The upload test writes to the real listening_tests.json (there is no
separate content dir in the app), so the fixture backs it up and
restores it afterwards, then reloads the lazy ContentStores.
"""
from __future__ import annotations

import copy
import json
import os

import pytest
from fastapi import HTTPException

from app.content import CONTENT_DIR, ContentStore, _validate_listening
from app.routers import audio as audio_router
from app.routers import mock as mock_router
from app.routers import practice as practice_router

from .conftest import client, user_headers

FAKE_MP3 = b"ID3" + bytes(997)  # 1000 bytes, valid ID3 magic
LISTENING_JSON = CONTENT_DIR / "listening_tests.json"


@pytest.fixture(autouse=True)
def _clear_admin_emails():
    previous = os.environ.pop("ADMIN_EMAILS", None)
    yield
    if previous is None:
        os.environ.pop("ADMIN_EMAILS", None)
    else:
        os.environ["ADMIN_EMAILS"] = previous


@pytest.fixture()
def audio_root(tmp_path, monkeypatch):
    root = tmp_path / "audio"
    root.mkdir()
    monkeypatch.setattr(audio_router, "AUDIO_ROOT", root)
    return root


@pytest.fixture()
def restore_listening_json():
    original = LISTENING_JSON.read_bytes()
    try:
        yield
    finally:
        LISTENING_JSON.write_bytes(original)
        practice_router.CONTENT.reload()
        mock_router.CONTENT.reload()


def _seed(root, test_id: str = "L1", part: int = 1) -> None:
    folder = root / test_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"part{part}.mp3").write_bytes(FAKE_MP3)


# -- Serving -----------------------------------------------------------

def test_serve_full_file(audio_root) -> None:
    _seed(audio_root)
    resp = client.get("/static/audio/listening/L1/part1.mp3")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.headers["accept-ranges"] == "bytes"
    assert resp.content == FAKE_MP3


def test_serve_partial_range(audio_root) -> None:
    _seed(audio_root)
    resp = client.get(
        "/static/audio/listening/L1/part1.mp3",
        headers={"Range": "bytes=100-199"},
    )
    assert resp.status_code == 206, resp.text
    assert resp.headers["content-range"] == "bytes 100-199/1000"
    assert resp.headers["content-length"] == "100"
    assert resp.content == FAKE_MP3[100:200]


def test_serve_open_ended_range(audio_root) -> None:
    _seed(audio_root)
    resp = client.get(
        "/static/audio/listening/L1/part1.mp3",
        headers={"Range": "bytes=900-"},
    )
    assert resp.status_code == 206
    assert resp.headers["content-range"] == "bytes 900-999/1000"
    assert resp.content == FAKE_MP3[900:]


def test_serve_suffix_range(audio_root) -> None:
    _seed(audio_root)
    resp = client.get(
        "/static/audio/listening/L1/part1.mp3",
        headers={"Range": "bytes=-10"},
    )
    assert resp.status_code == 206
    assert resp.headers["content-range"] == "bytes 990-999/1000"
    assert resp.content == FAKE_MP3[-10:]


def test_serve_unsatisfiable_range_is_416(audio_root) -> None:
    _seed(audio_root)
    resp = client.get(
        "/static/audio/listening/L1/part1.mp3",
        headers={"Range": "bytes=2000-3000"},
    )
    assert resp.status_code == 416
    assert resp.headers["content-range"] == "bytes */1000"


def test_serve_missing_file_is_404(audio_root) -> None:
    resp = client.get("/static/audio/listening/L1/part1.mp3")
    assert resp.status_code == 404


def test_serve_bad_ids_are_400(audio_root) -> None:
    for url in (
        "/static/audio/listening/L9/part1.mp3",
        "/static/audio/listening/L0/part1.mp3",
        "/static/audio/listening/L1/part5.mp3",
        "/static/audio/listening/L1/part0.mp3",
        "/static/audio/listening/TEST/part1.mp3",
    ):
        assert client.get(url).status_code == 400, url


def test_traversal_is_rejected(audio_root) -> None:
    # ".." never reaches the handler as a test_id; whatever the HTTP
    # layer does with it, it must never serve a file.
    resp = client.get("/static/audio/listening/../part1.mp3")
    assert resp.status_code in (400, 404)
    # The validator itself rejects traversal ids outright.
    with pytest.raises(HTTPException) as exc:
        audio_router._validate_ids("..", "1")
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        audio_router._validate_ids("L1", "..")
    assert exc.value.status_code == 400


# -- Upload ------------------------------------------------------------

def test_upload_requires_auth(audio_root) -> None:
    resp = client.post(
        "/api/audio/listening/L1/part1",
        files={"file": ("part1.mp3", FAKE_MP3, "audio/mpeg")},
    )
    assert resp.status_code == 401


def test_upload_forbidden_for_non_admin(audio_root, user_token: dict) -> None:
    resp = client.post(
        "/api/audio/listening/L1/part1",
        files={"file": ("part1.mp3", FAKE_MP3, "audio/mpeg")},
        headers=user_headers(user_token),
    )
    assert resp.status_code == 403


def test_upload_rejects_wrong_content_type(
    audio_root, user_token: dict
) -> None:
    os.environ["ADMIN_EMAILS"] = user_token["email"]
    resp = client.post(
        "/api/audio/listening/L1/part1",
        files={"file": ("part1.txt", b"not audio", "text/plain")},
        headers=user_headers(user_token),
    )
    assert resp.status_code == 400


def test_upload_rejects_non_mp3_bytes(
    audio_root, user_token: dict
) -> None:
    os.environ["ADMIN_EMAILS"] = user_token["email"]
    resp = client.post(
        "/api/audio/listening/L1/part1",
        files={"file": ("part1.mp3", b"this is not an mp3 at all", "audio/mpeg")},
        headers=user_headers(user_token),
    )
    assert resp.status_code == 400


def test_upload_rejects_bad_ids(audio_root, user_token: dict) -> None:
    os.environ["ADMIN_EMAILS"] = user_token["email"]
    resp = client.post(
        "/api/audio/listening/L9/part1",
        files={"file": ("part1.mp3", FAKE_MP3, "audio/mpeg")},
        headers=user_headers(user_token),
    )
    assert resp.status_code == 400


def test_upload_success_flips_audio_url_and_serves(
    audio_root, user_token: dict, restore_listening_json
) -> None:
    os.environ["ADMIN_EMAILS"] = user_token["email"]
    headers = user_headers(user_token)

    # Nothing recorded yet: the public view shows audio_url null.
    before = client.get("/api/practice/listening/L1", headers=headers)
    assert before.status_code == 200
    assert before.json()["parts"][0]["audio_url"] is None

    resp = client.post(
        "/api/audio/listening/L1/part1",
        files={"file": ("part1.mp3", FAKE_MP3, "audio/mpeg")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"audio_url": "/static/audio/listening/L1/part1.mp3"}

    # The new audio_url is served without a restart, and the public
    # listening view shows it immediately.
    served = client.get("/static/audio/listening/L1/part1.mp3")
    assert served.status_code == 200
    assert served.content == FAKE_MP3

    after = client.get("/api/practice/listening/L1", headers=headers)
    assert after.status_code == 200
    assert after.json()["parts"][0]["audio_url"] == (
        "/static/audio/listening/L1/part1.mp3"
    )

    # The JSON on disk carries the same value.
    with LISTENING_JSON.open(encoding="utf-8") as f:
        stored = json.load(f)
    stored_test = next(t for t in stored["tests"] if t["id"] == "L1")
    assert stored_test["parts"][0]["audio_url"] == (
        "/static/audio/listening/L1/part1.mp3"
    )


# -- Content rule ------------------------------------------------------

def test_audio_url_rule_accepts_matching_url() -> None:
    store = ContentStore()
    test = copy.deepcopy(store.listening("L3"))
    test["parts"][1]["audio_url"] = "/static/audio/listening/L3/part2.mp3"
    _validate_listening(test)  # must not raise


def test_audio_url_rule_rejects_mismatch() -> None:
    store = ContentStore()
    wrong_test = copy.deepcopy(store.listening("L3"))
    wrong_test["parts"][1]["audio_url"] = "/static/audio/listening/L4/part2.mp3"
    with pytest.raises(ValueError):
        _validate_listening(wrong_test)
    wrong_part = copy.deepcopy(store.listening("L3"))
    wrong_part["parts"][1]["audio_url"] = "/static/audio/listening/L3/part3.mp3"
    with pytest.raises(ValueError):
        _validate_listening(wrong_part)
    bad_path = copy.deepcopy(store.listening("L3"))
    bad_path["parts"][1]["audio_url"] = "https://example.com/audio.mp3"
    with pytest.raises(ValueError):
        _validate_listening(bad_path)
