"""Phase 2 practice: Listening + Reading timed tests with automatic
scoring, Writing guided practice, Speaking sets, and the content lists.

Answers are never sent to the client before a submit: the public test
views strip answers, explanations and evidence. Scoring happens
server-side from the original content, and every band estimate carries
the "practice estimate, not an official score" label.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..content import ContentStore
from ..database import get_db
from ..deps import get_current_user
from ..feedback import (
    WritingFeedbackRequest,
    WritingFeedbackResponse,
    analyse_writing,
)
from ..models import Attempt, TestSession, User
from ..scoring import (
    BAND_LABEL,
    LISTENING_TIME_LIMIT_SECONDS,
    READING_TIME_LIMIT_SECONDS,
    SUBMIT_GRACE_SECONDS,
    listening_band,
    overall_band,
    reading_band,
    short_answer_matches,
)
from ..schemas import (
    ListeningTestPublic,
    ListeningTestSummary,
    QuestionResult,
    ReadingTestPublic,
    ReadingTestSummary,
    SpeakingCompleteRequest,
    SpeakingCompleteResponse,
    SpeakingSet,
    StartRequest,
    StartResponse,
    SubmitRequest,
    SubmitResponse,
    TestPartSummary,
    WritingPromptFull,
    WritingPromptSummary,
    WritingSubmitRequest,
    WritingSubmitResponse,
)

router = APIRouter(prefix="/practice", tags=["practice"])


class _LazyContent:
    """Lazily loads the ContentStore on first use. Until the content
    files exist, any practice endpoint answers 503 instead of breaking
    the whole app at import time."""

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


def _all_questions(test: dict, key: str) -> list[dict]:
    questions: list[dict] = []
    for section in test[key]:
        questions.extend(section["questions"])
    return questions


def _score_question(q: dict, given: str | int | None) -> tuple[bool, str | int]:
    """Score one question. Returns (correct, correct_answer)."""
    if q["type"] == "mcq":
        correct_answer: str | int = q["options"][q["answer"]]
        if given is None:
            return False, correct_answer
        try:
            given_index = int(given)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False, correct_answer
        return given_index == q["answer"], correct_answer
    if q["type"] == "tfng":
        correct_answer = q["answer"]
        if given is None:
            return False, correct_answer
        return (
            str(given).strip().upper() == correct_answer.upper(),
            correct_answer,
        )
    # short / completion
    correct_answer = q["answers"][0]
    if given is None or not isinstance(given, str):
        return False, correct_answer
    return short_answer_matches(given, q["answers"]), correct_answer


def _score(test: dict, key: str, answers: dict[str, str | int]) -> tuple[int, list[QuestionResult]]:
    score = 0
    results: list[QuestionResult] = []
    for q in _all_questions(test, key):
        given = answers.get(str(q["no"]))
        correct, correct_answer = _score_question(q, given)
        if correct:
            score += 1
        results.append(
            QuestionResult(
                no=q["no"],
                correct=correct,
                your_answer=given,
                correct_answer=correct_answer,
                explanation=q["explanation"],
                evidence=q["evidence"],
            )
        )
    return score, results


def _load_session(
    session_id: int, module: str, test_id: str, user: User, db: Session
) -> TestSession:
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="This session belongs to another learner")
    if session.module != module or session.test_id != test_id:
        raise HTTPException(status_code=400, detail="Session does not match this test")
    if session.submitted:
        raise HTTPException(status_code=400, detail="This session was already submitted")
    return session


def _check_timed(session: TestSession) -> int:
    """Return elapsed seconds; refuse a timed submit past limit + grace."""
    started_at = session.started_at
    if started_at.tzinfo is None:
        # SQLite stores datetimes without tzinfo; treat them as UTC.
        started_at = started_at.replace(tzinfo=timezone.utc)
    elapsed = int((_now() - started_at).total_seconds())
    if session.mode == "timed" and session.time_limit_seconds is not None:
        if elapsed > session.time_limit_seconds + SUBMIT_GRACE_SECONDS:
            raise HTTPException(
                status_code=400,
                detail="Time expired — your answers were not scored. Start again.",
            )
    return max(0, elapsed)


def _start_session(
    module: str, test_id: str, mode: str, user: User, db: Session
) -> StartResponse:
    limit = (
        LISTENING_TIME_LIMIT_SECONDS
        if module == "listening"
        else READING_TIME_LIMIT_SECONDS
    )
    time_limit = limit if mode == "timed" else None
    started_at = _now()
    session = TestSession(
        user_id=user.id,
        module=module,
        test_id=test_id,
        mode=mode,
        started_at=started_at,
        time_limit_seconds=time_limit,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return StartResponse(
        session_id=session.id,
        started_at=started_at,
        time_limit_seconds=time_limit,
        expires_at=(started_at + timedelta(seconds=time_limit)) if time_limit else None,
    )


def _finish_session(
    session: TestSession,
    module: str,
    score_raw: int,
    band: float,
    duration_seconds: int,
    db: Session,
) -> Attempt:
    session.submitted = True
    attempt = Attempt(
        user_id=session.user_id,
        module=module,
        kind="mock" if session.mode == "timed" else "practice",
        score_raw=score_raw,
        band_estimate=band,
        duration_seconds=duration_seconds,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


# -- Listening ---------------------------------------------------------

@router.get("/listening", response_model=list[ListeningTestSummary])
def list_listening() -> list[ListeningTestSummary]:
    return [
        ListeningTestSummary(
            id=test["id"],
            title=test["title"],
            parts=[
                TestPartSummary(
                    part=part["part"],
                    title=part["title"],
                    question_count=len(part["questions"]),
                    has_audio=part["audio_url"] is not None,
                )
                for part in test["parts"]
            ],
            total_questions=40,
            time_limit_seconds=LISTENING_TIME_LIMIT_SECONDS,
        )
        for test in CONTENT.listening_tests
    ]


@router.get("/listening/{test_id}", response_model=ListeningTestPublic)
def get_listening(test_id: str) -> ListeningTestPublic:
    test = CONTENT.listening(test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Listening test not found")
    return ListeningTestPublic(**CONTENT.public_listening(test))


@router.post("/listening/{test_id}/start", response_model=StartResponse, status_code=201)
def start_listening(
    test_id: str,
    payload: StartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StartResponse:
    if CONTENT.listening(test_id) is None:
        raise HTTPException(status_code=404, detail="Listening test not found")
    return _start_session("listening", test_id, payload.mode, current_user, db)


@router.post("/listening/{test_id}/submit", response_model=SubmitResponse)
def submit_listening(
    test_id: str,
    payload: SubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmitResponse:
    test = CONTENT.listening(test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Listening test not found")
    session = _load_session(payload.session_id, "listening", test_id, current_user, db)
    duration = _check_timed(session)
    score, results = _score(test, "parts", payload.answers)
    band = listening_band(score)
    _finish_session(session, "listening", score, band, duration, db)
    return SubmitResponse(
        score_raw=score,
        band_estimate=band,
        band_label=BAND_LABEL,
        duration_seconds=duration,
        overtime=False,
        results=results,
    )


# -- Reading -----------------------------------------------------------

@router.get("/reading", response_model=list[ReadingTestSummary])
def list_reading(track: str = "academic") -> list[ReadingTestSummary]:
    if track not in ("academic", "general"):
        raise HTTPException(status_code=400, detail="track must be academic or general")
    return [
        ReadingTestSummary(
            id=test["id"],
            track=test["track"],
            title=test["title"],
            total_questions=40,
            time_limit_seconds=READING_TIME_LIMIT_SECONDS,
        )
        for test in CONTENT.reading_tests
        if test["track"] == track
    ]


@router.get("/reading/{test_id}", response_model=ReadingTestPublic)
def get_reading(test_id: str) -> ReadingTestPublic:
    test = CONTENT.reading(test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Reading test not found")
    return ReadingTestPublic(**CONTENT.public_reading(test))


@router.post("/reading/{test_id}/start", response_model=StartResponse, status_code=201)
def start_reading(
    test_id: str,
    payload: StartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StartResponse:
    if CONTENT.reading(test_id) is None:
        raise HTTPException(status_code=404, detail="Reading test not found")
    return _start_session("reading", test_id, payload.mode, current_user, db)


@router.post("/reading/{test_id}/submit", response_model=SubmitResponse)
def submit_reading(
    test_id: str,
    payload: SubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmitResponse:
    test = CONTENT.reading(test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="Reading test not found")
    session = _load_session(payload.session_id, "reading", test_id, current_user, db)
    duration = _check_timed(session)
    score, results = _score(test, "passages", payload.answers)
    band = reading_band(test["track"], score)
    _finish_session(session, "reading", score, band, duration, db)
    return SubmitResponse(
        score_raw=score,
        band_estimate=band,
        band_label=BAND_LABEL,
        duration_seconds=duration,
        overtime=False,
        results=results,
    )


# -- Writing -----------------------------------------------------------

@router.get("/writing", response_model=list[WritingPromptSummary])
def list_writing(track: str = "academic") -> list[WritingPromptSummary]:
    if track not in ("academic", "general"):
        raise HTTPException(status_code=400, detail="track must be academic or general")
    return [
        WritingPromptSummary(**CONTENT.public_writing_prompt(prompt))
        for prompt in CONTENT.writing_prompts
        if prompt["track"] == track
    ]


@router.get("/writing/{prompt_id}", response_model=WritingPromptFull)
def get_writing(prompt_id: str) -> WritingPromptFull:
    prompt = CONTENT.writing(prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Writing prompt not found")
    return WritingPromptFull(**prompt)


@router.post("/writing/submit", response_model=WritingSubmitResponse, status_code=201)
def submit_writing(
    payload: WritingSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WritingSubmitResponse:
    prompt = CONTENT.writing(payload.prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Writing prompt not found")
    word_count = len(payload.text.split())
    meets_minimum = word_count >= prompt["min_words"]
    attempt = Attempt(
        user_id=current_user.id,
        module="writing",
        kind="practice",
        score_raw=None,
        band_estimate=None,
        duration_seconds=payload.duration_seconds,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return WritingSubmitResponse(
        word_count=word_count,
        min_words=prompt["min_words"],
        meets_minimum=meets_minimum,
        attempt_id=attempt.id,
    )


@router.post("/writing/feedback", response_model=WritingFeedbackResponse)
def writing_feedback(
    payload: WritingFeedbackRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Automated Writing feedback: a band range per criterion plus notes.

    Guidance only — the response always carries the practice-estimate
    label and the limits statement. No attempt is recorded here; use
    POST /writing/submit to save a practice attempt.
    """
    prompt = CONTENT.writing(payload.prompt_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Writing prompt not found")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")
    return analyse_writing(prompt, payload.text)


# -- Speaking ----------------------------------------------------------

@router.get("/speaking", response_model=list[SpeakingSet])
def list_speaking() -> list[SpeakingSet]:
    return [SpeakingSet(**entry) for entry in CONTENT.speaking_sets]


@router.post("/speaking/complete", response_model=SpeakingCompleteResponse, status_code=201)
def complete_speaking(
    payload: SpeakingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SpeakingCompleteResponse:
    if CONTENT.speaking(payload.set_id) is None:
        raise HTTPException(status_code=404, detail="Speaking set not found")
    attempt = Attempt(
        user_id=current_user.id,
        module="speaking",
        kind="practice",
        score_raw=None,
        band_estimate=None,
        duration_seconds=payload.duration_seconds,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return SpeakingCompleteResponse(attempt_id=attempt.id)


# -- Overall band helper (used by the dashboard) -----------------------

def latest_bands(db: Session, user_id: int) -> dict[str, float | None]:
    """Latest band per module from scored attempts, or None."""
    from ..schemas import MODULES

    latest: dict[str, float | None] = {module: None for module in MODULES}
    rows = (
        db.query(Attempt)
        .filter(Attempt.user_id == user_id, Attempt.band_estimate.isnot(None))
        .order_by(Attempt.created_at.desc())
        .all()
    )
    for row in rows:
        if latest[row.module] is None:
            latest[row.module] = row.band_estimate
    return latest


def overall_estimate(db: Session, user_id: int) -> float | None:
    latest = latest_bands(db, user_id)
    bands = [latest[m] for m in ("listening", "reading", "writing", "speaking")]
    if any(b is None for b in bands):
        return None
    return overall_band([b for b in bands if b is not None])
