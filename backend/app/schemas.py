"""Pydantic schemas for the PrepSathi API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

MODULES = ("listening", "reading", "writing", "speaking")


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(default="", max_length=120)
    target_band_overall: float | None = Field(default=None, ge=0, le=9)
    target_band_writing: float | None = Field(default=None, ge=0, le=9)


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    target_band_overall: float | None
    target_band_writing: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ModuleInfo(BaseModel):
    slug: str
    name: str
    time_minutes: str
    questions: str
    description: str
    status: str


class ResourceLink(BaseModel):
    title: str
    url: str
    description: str
    provider: str


class AttemptCreate(BaseModel):
    module: str
    kind: str = Field(default="practice", pattern="^(practice|mock)$")
    score_raw: int | None = Field(default=None, ge=0)
    band_estimate: float | None = Field(default=None, ge=0, le=9)
    duration_seconds: int | None = Field(default=None, ge=0)


class AttemptOut(BaseModel):
    id: int
    module: str
    kind: str
    score_raw: int | None
    band_estimate: float | None
    band_label: str | None
    duration_seconds: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VocabularyCreate(BaseModel):
    word: str = Field(min_length=1, max_length=120)
    meaning: str = Field(default="", max_length=2000)
    topic: str = Field(default="general", max_length=80)


class VocabularyOut(BaseModel):
    id: int
    word: str
    meaning: str
    example: str
    topic: str
    interval_days: int
    next_review: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    attempts_total: int
    attempts_by_module: dict[str, int]
    vocabulary_total: int
    vocabulary_due: int
    target_band_overall: float | None
    target_band_writing: float | None
    latest_band_by_module: dict[str, float | None]
    overall_estimate: float | None
    attempts_recent: list[AttemptOut]


# --- Phase 2: practice -------------------------------------------------

class TestPartSummary(BaseModel):
    part: int
    title: str
    question_count: int
    has_audio: bool


class ListeningTestSummary(BaseModel):
    id: str
    title: str
    parts: list[TestPartSummary]
    total_questions: int
    time_limit_seconds: int


class ListeningQuestionPublic(BaseModel):
    no: int
    type: str
    prompt: str
    options: list[str] | None = None


class ListeningPartPublic(BaseModel):
    part: int
    title: str
    setting: str
    transcript: str
    audio_url: str | None = None
    audio_note: str
    questions: list[ListeningQuestionPublic]


class ListeningTestPublic(BaseModel):
    id: str
    title: str
    parts: list[ListeningPartPublic]


class ReadingTestSummary(BaseModel):
    id: str
    track: str
    title: str
    total_questions: int
    time_limit_seconds: int


class ReadingQuestionPublic(BaseModel):
    no: int
    type: str
    prompt: str
    options: list[str] | None = None


class ReadingPassagePublic(BaseModel):
    section: int
    title: str
    text: str
    questions: list[ReadingQuestionPublic]


class ReadingTestPublic(BaseModel):
    id: str
    track: str
    title: str
    passages: list[ReadingPassagePublic]


class StartRequest(BaseModel):
    mode: str = Field(default="practice", pattern="^(timed|practice)$")


class StartResponse(BaseModel):
    session_id: int
    started_at: datetime
    time_limit_seconds: int | None
    expires_at: datetime | None


class SubmitRequest(BaseModel):
    session_id: int
    answers: dict[str, str | int]


class QuestionResult(BaseModel):
    no: int
    correct: bool
    your_answer: str | int | None
    correct_answer: str | int
    explanation: str
    evidence: str


class SubmitResponse(BaseModel):
    score_raw: int
    band_estimate: float
    band_label: str
    duration_seconds: int
    overtime: bool
    results: list[QuestionResult]


class WritingPromptSummary(BaseModel):
    id: str
    track: str
    task: int
    title: str
    prompt: str
    min_words: int
    suggested_minutes: int


class WritingPromptFull(WritingPromptSummary):
    model_answer: str
    commentary: str


class WritingSubmitRequest(BaseModel):
    prompt_id: str
    text: str = Field(min_length=1, max_length=20000)
    duration_seconds: int | None = Field(default=None, ge=0)


class WritingSubmitResponse(BaseModel):
    word_count: int
    min_words: int
    meets_minimum: bool
    attempt_id: int


class SpeakingPart2(BaseModel):
    cue: str
    points: list[str]
    prep_seconds: int
    talk_seconds: int


class SpeakingSet(BaseModel):
    id: str
    topic: str
    part1: list[str]
    part2: SpeakingPart2
    part3: list[str]
    sample_answer: str


class SpeakingCompleteRequest(BaseModel):
    set_id: str
    duration_seconds: int | None = Field(default=None, ge=0)


class SpeakingCompleteResponse(BaseModel):
    attempt_id: int


class VocabularyReviewRequest(BaseModel):
    correct: bool


class SeedResponse(BaseModel):
    added: int
    skipped: int


# --- Phase 3: full mock sittings --------------------------------------

class MockStartRequest(BaseModel):
    track: str = Field(pattern="^(academic|general)$")


class MockStartResponse(BaseModel):
    mock_id: int
    track: str
    current_section: str
    listening_test_id: str
    reading_test_id: str
    writing_task1_prompt_id: str
    writing_task2_prompt_id: str
    started_at: datetime
    section_expires_at: datetime | None
    band_label: str


class MockSummary(BaseModel):
    mock_id: int
    track: str
    status: str
    current_section: str
    overall_band: float | None
    started_at: datetime


class MockScoredSection(BaseModel):
    status: str
    score_raw: int | None
    band_estimate: float | None


class MockWritingSection(BaseModel):
    status: str
    band_low: float | None
    band_high: float | None


class MockSpeakingSection(BaseModel):
    status: str
    band_estimate: float | None


class MockSections(BaseModel):
    listening: MockScoredSection
    reading: MockScoredSection
    writing: MockWritingSection
    speaking: MockSpeakingSection


class MockDetailResponse(BaseModel):
    mock_id: int
    track: str
    status: str
    current_section: str
    started_at: datetime
    section_expires_at: datetime | None
    sections: MockSections
    overall_band: float | None
    band_label: str


class MockSubmitResponse(SubmitResponse):
    next_section: str
    section_expires_at: datetime | None


class MockWritingSubmitRequest(BaseModel):
    task1_text: str = Field(min_length=1, max_length=20000)
    task2_text: str = Field(min_length=1, max_length=20000)
    duration_seconds: int | None = Field(default=None, ge=0)


class MockWritingTaskResult(BaseModel):
    word_count: int
    min_words: int
    meets_minimum: bool
    feedback: dict


class MockWritingSubmitResponse(BaseModel):
    task1: MockWritingTaskResult
    task2: MockWritingTaskResult
    writing_band_low: float
    writing_band_high: float
    next_section: str


class MockSpeakingCompleteRequest(BaseModel):
    set_id: str
    duration_seconds: int | None = Field(default=None, ge=0)
    band_low: float | None = Field(default=None, ge=0, le=9)
    band_high: float | None = Field(default=None, ge=0, le=9)


class MockSpeakingCompleteResponse(BaseModel):
    overall_band: float | None
    band_label: str
    status: str


# --- Phase 4: in-app feedback loop ------------------------------------

FEEDBACK_CATEGORIES = ("bug", "content", "feature", "other")


class FeedbackCreate(BaseModel):
    category: str = Field(pattern="^(bug|content|feature|other)$")
    message: str = Field(min_length=1, max_length=2000)
    page: str | None = Field(default=None, max_length=120)

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be blank")
        return stripped


class FeedbackUpdate(BaseModel):
    resolved: bool


class FeedbackOut(BaseModel):
    id: int
    user_id: int
    category: str
    message: str
    page: str | None
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}
