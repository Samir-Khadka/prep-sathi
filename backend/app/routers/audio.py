"""Listening audio pipeline (Phase 5.2).

Recordings are real human voices only — never synthesised, never
placeholder audio. No audio files ship with the repo yet; an admin
uploads each part's MP3 and the matching ``audio_url`` is written into
listening_tests.json, so the file is served immediately, no restart.

Shared audio contract (the mobile app uses the same one):
- File layout: ``backend/app/static/audio/listening/<TEST_ID>/part<N>.mp3``
- Served URL: ``/static/audio/listening/<TEST_ID>/part<N>.mp3`` (relative)
- Clients resolve a relative audio_url against the API base URL.

Serving is done by this router (not StaticFiles) so Range requests are
handled explicitly: browsers seek with ``Range: bytes=...`` and a 206
partial response must never be cached as if it were the whole file.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status

from ..content import CONTENT_DIR, _validate_listening
from ..models import User
from .feedback_loop import get_admin_user

router = APIRouter(tags=["audio"])

# Overridable for tests (monkeypatch ``audio.AUDIO_ROOT`` to a temp dir).
AUDIO_ROOT: Path = Path(
    os.environ.get(
        "PREPSATHI_AUDIO_ROOT",
        str(Path(__file__).resolve().parent.parent / "static" / "audio" / "listening"),
    )
)

LISTENING_CONTENT_FILE: Path = CONTENT_DIR / "listening_tests.json"

MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20 MB per part

_TEST_ID_RE = re.compile(r"^L[1-8]$")
_PART_RE = re.compile(r"^[1-4]$")


def _validate_ids(test_id: str, part: str) -> tuple[str, int]:
    """Reject anything that is not a real test/part — including ``..``
    traversal — with 400 before any path is built."""
    if not _TEST_ID_RE.match(test_id) or not _PART_RE.match(part):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="test_id must be L1..L8 and part must be 1..4",
        )
    return test_id, int(part)


def _audio_path(test_id: str, part_no: int) -> Path:
    """Resolve the file path and prove it stays inside AUDIO_ROOT."""
    root = AUDIO_ROOT.resolve()
    path = (root / test_id / f"part{part_no}.mp3").resolve()
    if not path.is_relative_to(root):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio path",
        )
    return path


def _parse_range(range_header: str | None, size: int) -> tuple[int, int] | None:
    """Parse a single ``Range: bytes=start-end`` header.

    Returns (start, end) inclusive, or None for a full-file response.
    Raises ValueError for a malformed or unsatisfiable range.
    """
    if not range_header:
        return None
    if not range_header.startswith("bytes="):
        raise ValueError("range unit must be bytes")
    spec = range_header[len("bytes="):].strip()
    if "," in spec:  # multi-range requests are not supported
        raise ValueError("multiple ranges are not supported")
    if spec.startswith("-"):
        # Suffix range: last N bytes.
        try:
            suffix = int(spec[1:])
        except ValueError:
            raise ValueError("bad suffix range") from None
        if suffix <= 0:
            raise ValueError("bad suffix range")
        start = max(0, size - suffix)
        return start, size - 1
    parts = spec.split("-", 1)
    try:
        start = int(parts[0])
        end = int(parts[1]) if parts[1] else size - 1
    except ValueError:
        raise ValueError("bad range") from None
    if start < 0 or end < start or start >= size:
        raise ValueError("range not satisfiable")
    return start, min(end, size - 1)


@router.get("/static/audio/listening/{test_id}/part{part}.mp3")
def serve_listening_audio(test_id: str, part: str, request: Request) -> Response:
    test_id, part_no = _validate_ids(test_id, part)
    path = _audio_path(test_id, part_no)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio for this part has not been recorded yet",
        )
    data = path.read_bytes()
    size = len(data)
    headers = {
        "Content-Type": "audio/mpeg",
        "Accept-Ranges": "bytes",
    }
    try:
        wanted = _parse_range(request.headers.get("range"), size)
    except ValueError:
        return Response(
            content=b"",
            status_code=416,
            headers={**headers, "Content-Range": f"bytes */{size}"},
        )
    if wanted is None:
        return Response(
            content=data,
            status_code=200,
            headers={**headers, "Content-Length": str(size)},
        )
    start, end = wanted
    chunk = data[start:end + 1]
    return Response(
        content=chunk,
        status_code=206,
        headers={
            **headers,
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Content-Length": str(len(chunk)),
        },
    )


def _is_mp3(data: bytes) -> bool:
    """MP3 magic bytes: an ID3 tag, or an MPEG frame sync (0xFFEx)."""
    if data[:3] == b"ID3":
        return True
    return len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


@router.post("/api/audio/listening/{test_id}/part{part}")
async def upload_listening_audio(
    test_id: str,
    part: str,
    file: UploadFile = File(...),
    _admin: User = Depends(get_admin_user),
) -> dict:
    test_id, part_no = _validate_ids(test_id, part)
    if file.content_type != "audio/mpeg":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an MP3 (audio/mpeg)",
        )
    data = await file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file must be 20 MB or smaller",
        )
    if not data or not _is_mp3(data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid MP3",
        )

    # Write the file first, then flip the content flag.
    path = _audio_path(test_id, part_no)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    audio_url = f"/static/audio/listening/{test_id}/part{part_no}.mp3"
    with LISTENING_CONTENT_FILE.open(encoding="utf-8") as f:
        content = json.load(f)
    tests = content.get("tests", [])
    test = next((t for t in tests if t.get("id") == test_id), None)
    if test is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Listening test not found",
        )
    test["parts"][part_no - 1]["audio_url"] = audio_url
    _validate_listening(test)  # fail loudly before writing a bad file
    with LISTENING_CONTENT_FILE.open("w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # The lazy ContentStores in practice + mock cache the old file:
    # drop them so the new audio_url is served without a restart.
    from . import mock as mock_router
    from . import practice as practice_router

    practice_router.CONTENT.reload()
    mock_router.CONTENT.reload()
    return {"audio_url": audio_url}
