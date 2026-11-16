"""Phase 3 mock sittings: a full Listening → Reading → Writing →
Speaking test in order, with a server-side clock per section.

A mock runs in test order and you cannot go back: submitting a section
that is not current is rejected. A section that runs out of time is
marked expired (Listening/Reading: score 0 / band 1.0) and the sitting
moves on, so a missed section never blocks the rest of the mock. Every
band is a practice estimate, never an official score.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..content import ContentStore
from ..database import get_db
from ..deps import get_current_user
from ..models import Attempt, MockSession, TestSession, User
from ..routers.practice import _check_timed, _load_session, _score
from ..scoring import (
    BAND_LABEL,
    LISTENING_TIME_LIMIT_SECONDS,
    READING_TIME_LIMIT_SECONDS,
    SUBMIT_GRACE_SECONDS,
    listening_band,
    overall_band,
    reading_band,
)
from ..schemas import (
    MockDetailResponse,
    MockScoredSection,
    MockSections,
    MockSpeakingCompleteRequest,
    MockSpeakingCompleteResponse,
    MockSpeakingSection,
    MockStartRequest,
    MockStartResponse,
    MockSubmitResponse,
    MockSummary,
    MockWritingSection,
    MockWritingSubmitRequest,
    MockWritingSubmitResponse,
    MockWritingTaskResult,
    SubmitRequest,
)

router = APIRouter(prefix="/mock", tags=["mock"])

# Test combinations, in rotation order per track. A learner's n-th mock
# of a track uses pair n (wrapping), so a second mock uses fresh material.
ACADEMIC_PAIRS: list[tuple[str, str]] = [
    ("L1", "RA1"),
    ("L2", "RA2"),
    ("L3", "RA3"),
    ("L4", "RA4"),
]
GENERAL_PAIRS: list[tuple[str, str]] = [
    ("L1", "RG1"),
    ("L2", "RG1"),
    ("L3", "RG1"),
    ("L4", "RG1"),
]
WRITING_TIME_LIMIT_SECONDS = 3600

CLOSED_SECTION_DETAIL = (
    "That section is closed — a mock runs in test order and you cannot go back"
)


class _LazyContent:
    """Lazily loads the ContentStore on first use, like practice.py."""

    _store: ContentStore | None = None

    def __getattr__(self, name: str):
        if self._store is None:
            try:
                self._store = ContentStore()
            except Exception as exc:
                raise HTTPException(
                    status_code=503,
                    detail="Practice content is not available yet",
                ) from exc
        return getattr(self._store, name)


CONTENT = _LazyContent()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    # SQLite stores datetimes without tzinfo; treat them as UTC.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _load_mock(mock_id: int, user: User, db: Session) -> MockSession:
    mock = db.query(MockSession).filter(MockSession.id == mock_id).first()
    if mock is None:
        raise HTTPException(status_code=404, detail="Mock not found")
    if mock.user_id != user.id:
        raise HTTPException(
            status_code=403, detail="This mock belongs to another learner"
        )
    return mock


def _require_current(mock: MockSession, section: str) -> None:
    if mock.current_section != section:
        raise HTTPException(status_code=400, detail=CLOSED_SECTION_DETAIL)


def _writing_midpoint(mock: MockSession) -> float | None:
    if mock.writing_band_low is None or mock.writing_band_high is None:
        return None
    return (mock.writing_band_low + mock.writing_band_high) / 2


def _overall(mock: MockSession) -> float | None:
    """Overall band, or None until all four sections have a band."""
    writing = _writing_midpoint(mock)
    bands = [mock.listening_band, mock.reading_band, writing, mock.speaking_band]
    if any(band is None for band in bands):
        return None
    return overall_band([band for band in bands if band is not None])


def _section_status(mock: MockSession, section: str) -> str:
    if section == "listening":
        if mock.listening_band is not None:
            return "expired" if mock.listening_expired else "done"
    elif section == "reading":
        if mock.reading_band is not None:
            return "expired" if mock.reading_expired else "done"
    elif section == "writing":
        if mock.writing_band_low is not None:
            return "done"
        if mock.writing_expired:
            return "expired"
    elif section == "speaking":
        if mock.speaking_band is not None:
            return "done"
    if mock.current_section == section:
        return "active"
    return "pending"


def _sections(mock: MockSession) -> MockSections:
    return MockSections(
        listening=MockScoredSection(
            status=_section_status(mock, "listening"),
            score_raw=mock.listening_score_raw,
            band_estimate=mock.listening_band,
        ),
        reading=MockScoredSection(
            status=_section_status(mock, "reading"),
            score_raw=mock.reading_score_raw,
            band_estimate=mock.reading_band,
        ),
        writing=MockWritingSection(
            status=_section_status(mock, "writing"),
            band_low=mock.writing_band_low,
            band_high=mock.writing_band_high,
        ),
        speaking=MockSpeakingSection(
            status=_section_status(mock, "speaking"),
            band_estimate=mock.speaking_band,
        ),
    )


def _advance(mock: MockSession, next_section: str, clock_seconds: int | None) -> None:
    """Move the mock to the next section and start its clock (if any)."""
    now = _now()
    mock.current_section = next_section
    mock.section_started_at = now
    mock.section_expires_at = (
        now + timedelta(seconds=clock_seconds) if clock_seconds else None
    )


def _pick_pair(track: str, user_id: int, db: Session) -> tuple[str, str]:
    pairs = ACADEMIC_PAIRS if track == "academic" else GENERAL_PAIRS
    used = (
        db.query(MockSession)
        .filter(MockSession.user_id == user_id, MockSession.track == track)
        .count()
    )
    return pairs[used % len(pairs)]


def _pick_writing_prompt(
    track: str, task: int, user_id: int, db: Session
) -> str:
    """First unused prompt of this track/task, in definition order;
    wraps to the first prompt once every prompt has been used."""
    ordered = [
        p["id"]
        for p in CONTENT.writing_prompts
        if p["track"] == track and p["task"] == task
    ]
    column = (
        MockSession.writing_task1_prompt_id
        if task == 1
        else MockSession.writing_task2_prompt_id
    )
    used = {
        row[0]
        for row in db.query(column)
        .filter(MockSession.user_id == user_id, MockSession.track == track)
        .all()
    }
    for prompt_id in ordered:
        if prompt_id not in used:
            return prompt_id
    return ordered[0]


def _record_attempt(
    user_id: int,
    module: str,
    score_raw: int | None,
    band: float | None,
    duration_seconds: int | None,
    db: Session,
) -> Attempt:
    attempt = Attempt(
        user_id=user_id,
        module=module,
        kind="mock",
        score_raw=score_raw,
        band_estimate=band,
        duration_seconds=duration_seconds,
    )
    db.add(attempt)
    return attempt


def _elapsed_seconds(session: TestSession) -> int:
    return max(0, int((_now() - _aware(session.started_at)).total_seconds()))


# -- Start / list / detail ------------------------------------------------

@router.post("/start", response_model=MockStartResponse, status_code=201)
def start_mock(
    payload: MockStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MockStartResponse:
    listening_id, reading_id = _pick_pair(payload.track, current_user.id, db)
    task1_id = _pick_writing_prompt(payload.track, 1, current_user.id, db)
    task2_id = _pick_writing_prompt(payload.track, 2, current_user.id, db)
    now = _now()
    mock = MockSession(
        user_id=current_user.id,
        track=payload.track,
        listening_test_id=listening_id,
        reading_test_id=reading_id,
        writing_task1_prompt_id=task1_id,
        writing_task2_prompt_id=task2_id,
        current_section="listening",
        started_at=now,
        section_started_at=now,
        section_expires_at=now
        + timedelta(seconds=LISTENING_TIME_LIMIT_SECONDS),
        status="in_progress",
    )
    db.add(mock)
    db.commit()
    db.refresh(mock)
    return MockStartResponse(
        mock_id=mock.id,
        track=mock.track,
        current_section=mock.current_section,
        listening_test_id=mock.listening_test_id,
        reading_test_id=mock.reading_test_id,
        writing_task1_prompt_id=mock.writing_task1_prompt_id,
        writing_task2_prompt_id=mock.writing_task2_prompt_id,
        started_at=mock.started_at,
        section_expires_at=mock.section_expires_at,
        band_label=BAND_LABEL,
    )


@router.get("", response_model=list[MockSummary])
def list_mocks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MockSummary]:
    mocks = (
        db.query(MockSession)
        .filter(MockSession.user_id == current_user.id)
        .order_by(MockSession.started_at.desc(), MockSession.id.desc())
        .all()
    )
    return [
        MockSummary(
            mock_id=mock.id,
            track=mock.track,
            status=mock.status,
            current_section=mock.current_section,
            overall_band=_overall(mock),
            started_at=mock.started_at,
        )
        for mock in mocks
    ]


@router.get("/{mock_id}", response_model=MockDetailResponse)
def get_mock(
    mock_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MockDetailResponse:
    mock = _load_mock(mock_id, current_user, db)
    return MockDetailResponse(
        mock_id=mock.id,
        track=mock.track,
        status=mock.status,
        current_section=mock.current_section,
        started_at=mock.started_at,
        section_expires_at=mock.section_expires_at,
        sections=_sections(mock),
        overall_band=_overall(mock),
        band_label=BAND_LABEL,
    )


# -- Listening / Reading submits ------------------------------------------

def _submit_scored(
    mock: MockSession,
    module: str,
    payload: SubmitRequest,
    user: User,
    db: Session,
) -> MockSubmitResponse:
    """Shared Listening/Reading submit: score, or mark expired and move on."""
    if module == "listening":
        test_id = mock.listening_test_id
        key = "parts"
        next_section = "reading"
        next_clock = READING_TIME_LIMIT_SECONDS
    else:
        test_id = mock.reading_test_id
        key = "passages"
        next_section = "writing"
        next_clock = WRITING_TIME_LIMIT_SECONDS
    test = CONTENT.listening(test_id) if module == "listening" else CONTENT.reading(test_id)
    if test is None:
        raise HTTPException(status_code=404, detail=f"{module.title()} test not found")
    session = _load_session(payload.session_id, module, test_id, user, db)
    try:
        duration = _check_timed(session)
    except HTTPException:
        # Past limit + grace: no score, no Attempt — mark the section
        # expired with 0 / band 1.0 and advance anyway.
        session.submitted = True
        if module == "listening":
            mock.listening_score_raw = 0
            mock.listening_band = 1.0
            mock.listening_expired = True
        else:
            mock.reading_score_raw = 0
            mock.reading_band = 1.0
            mock.reading_expired = True
        _advance(mock, next_section, next_clock)
        db.commit()
        return MockSubmitResponse(
            score_raw=0,
            band_estimate=1.0,
            band_label=BAND_LABEL,
            duration_seconds=_elapsed_seconds(session),
            overtime=True,
            results=[],
            next_section=next_section,
            section_expires_at=mock.section_expires_at,
        )
    score, results = _score(test, key, payload.answers)
    band = (
        listening_band(score)
        if module == "listening"
        else reading_band(mock.track, score)
    )
    session.submitted = True
    _record_attempt(user.id, module, score, band, duration, db)
    if module == "listening":
        mock.listening_score_raw = score
        mock.listening_band = band
    else:
        mock.reading_score_raw = score
        mock.reading_band = band
    _advance(mock, next_section, next_clock)
    db.commit()
    return MockSubmitResponse(
        score_raw=score,
        band_estimate=band,
        band_label=BAND_LABEL,
        duration_seconds=duration,
        overtime=False,
        results=results,
        next_section=next_section,
        section_expires_at=mock.section_expires_at,
    )


@router.post("/{mock_id}/listening/submit", response_model=MockSubmitResponse)
def submit_mock_listening(
    mock_id: int,
    payload: SubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MockSubmitResponse:
    mock = _load_mock(mock_id, current_user, db)
    _require_current(mock, "listening")
    return _submit_scored(mock, "listening", payload, current_user, db)


@router.post("/{mock_id}/reading/submit", response_model=MockSubmitResponse)
def submit_mock_reading(
    mock_id: int,
    payload: SubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MockSubmitResponse:
    mock = _load_mock(mock_id, current_user, db)
    _require_current(mock, "reading")
    return _submit_scored(mock, "reading", payload, current_user, db)


# -- Writing submit -------------------------------------------------------

@router.post("/{mock_id}/writing/submit", response_model=MockWritingSubmitResponse)
def submit_mock_writing(
    mock_id: int,
    payload: MockWritingSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MockWritingSubmitResponse:
    mock = _load_mock(mock_id, current_user, db)
    _require_current(mock, "writing")
    elapsed = int((_now() - _aware(mock.section_started_at)).total_seconds())
    if elapsed > WRITING_TIME_LIMIT_SECONDS + SUBMIT_GRACE_SECONDS:
        # Late: no feedback, no Attempt — mark the section expired with no
        # band range and advance to speaking.
        mock.writing_expired = True
        _advance(mock, "speaking", None)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=(
                "Writing time expired — the section is marked expired "
                "and the mock moves to speaking."
            ),
        )
    # Imported lazily: feedback.py is owned by a parallel build and may
    # not exist yet when this module is imported.
    try:
        from ..feedback import analyse_writing
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Writing feedback is not available yet",
        ) from exc
    results: dict[str, MockWritingTaskResult] = {}
    lows: list[float] = []
    highs: list[float] = []
    for key, prompt_id, text in (
        ("task1", mock.writing_task1_prompt_id, payload.task1_text),
        ("task2", mock.writing_task2_prompt_id, payload.task2_text),
    ):
        prompt = CONTENT.writing(prompt_id)
        if prompt is None:
            raise HTTPException(status_code=404, detail="Writing prompt not found")
        feedback = analyse_writing(prompt, text)
        results[key] = MockWritingTaskResult(
            word_count=feedback["word_count"],
            min_words=feedback["min_words"],
            meets_minimum=feedback["meets_minimum"],
            feedback=feedback,
        )
        lows.append(float(feedback["band_low"]))
        highs.append(float(feedback["band_high"]))
        _record_attempt(
            current_user.id,
            "writing",
            None,
            (float(feedback["band_low"]) + float(feedback["band_high"])) / 2,
            payload.duration_seconds,
            db,
        )
    mock.writing_band_low = sum(lows) / len(lows)
    mock.writing_band_high = sum(highs) / len(highs)
    _advance(mock, "speaking", None)
    db.commit()
    return MockWritingSubmitResponse(
        task1=results["task1"],
        task2=results["task2"],
        writing_band_low=mock.writing_band_low,
        writing_band_high=mock.writing_band_high,
        next_section="speaking",
    )


# -- Speaking complete ----------------------------------------------------

@router.post(
    "/{mock_id}/speaking/complete",
    response_model=MockSpeakingCompleteResponse,
)
def complete_mock_speaking(
    mock_id: int,
    payload: MockSpeakingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MockSpeakingCompleteResponse:
    mock = _load_mock(mock_id, current_user, db)
    _require_current(mock, "speaking")
    if CONTENT.speaking(payload.set_id) is None:
        raise HTTPException(status_code=404, detail="Speaking set not found")
    if (payload.band_low is None) != (payload.band_high is None):
        raise HTTPException(
            status_code=400,
            detail="Provide both band_low and band_high, or neither",
        )
    speaking_band: float | None = None
    if payload.band_low is not None and payload.band_high is not None:
        if payload.band_low > payload.band_high:
            raise HTTPException(
                status_code=400, detail="band_low must not exceed band_high"
            )
        speaking_band = (payload.band_low + payload.band_high) / 2
    _record_attempt(
        current_user.id,
        "speaking",
        None,
        speaking_band,
        payload.duration_seconds,
        db,
    )
    if speaking_band is not None:
        mock.speaking_band = speaking_band
        # The sitting is over once speaking has a band; it is only
        # "complete" when all four section bands exist (an expired
        # writing section can never produce a band, so the overall
        # stays null in that case).
        mock.current_section = "done"
        mock.section_expires_at = None
        overall = _overall(mock)
        if overall is not None:
            mock.status = "complete"
            mock.completed_at = _now()
    db.commit()
    return MockSpeakingCompleteResponse(
        overall_band=_overall(mock),
        band_label=BAND_LABEL,
        status=mock.status,
    )
