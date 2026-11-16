"""Database models for PrepSathi (Phase 1 skeleton).

- User: account + target bands.
- Attempt: one practice or mock attempt. Phase 1 only records attempts;
  scoring and band estimates arrive in Phase 2. A band_estimate, when
  present, is ALWAYS a practice estimate, never an official score.
- TestSession: one started Listening/Reading sitting; timed mode is
  enforced server-side from started_at + time_limit.
- VocabularyItem: one flashcard with spaced-repetition fields.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    target_band_overall: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    target_band_writing: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="user", cascade="all, delete-orphan"
    )
    test_sessions: Mapped[list["TestSession"]] = relationship(
        "TestSession", back_populates="user", cascade="all, delete-orphan"
    )
    vocabulary: Mapped[list["VocabularyItem"]] = relationship(
        "VocabularyItem", back_populates="user", cascade="all, delete-orphan"
    )
    mock_sessions: Mapped[list["MockSession"]] = relationship(
        "MockSession", back_populates="user", cascade="all, delete-orphan"
    )
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    module: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="practice")
    score_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    band_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="attempts")


class TestSession(Base):
    """One started Listening/Reading test sitting.

    Timed mode is enforced server-side: a timed submit is refused once
    the session's started_at + time_limit + grace has passed.
    """

    __tablename__ = "test_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    module: Mapped[str] = mapped_column(String(20), nullable=False)
    test_id: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="practice")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    time_limit_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="test_sessions")


class MockSession(Base):
    """One full mock sitting: Listening → Reading → Writing → Speaking,
    in test order, with a server-side clock per section.

    Section results live in columns (a band of 1.0 with the matching
    ``*_expired`` flag means the section expired unanswered). A band is
    always a practice estimate, never an official score.
    """

    __tablename__ = "mock_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    track: Mapped[str] = mapped_column(String(20), nullable=False)
    listening_test_id: Mapped[str] = mapped_column(String(20), nullable=False)
    reading_test_id: Mapped[str] = mapped_column(String(20), nullable=False)
    writing_task1_prompt_id: Mapped[str] = mapped_column(String(20), nullable=False)
    writing_task2_prompt_id: Mapped[str] = mapped_column(String(20), nullable=False)
    current_section: Mapped[str] = mapped_column(
        String(20), nullable=False, default="listening"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    section_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    section_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    listening_score_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    listening_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    listening_expired: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    reading_score_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reading_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_expired: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    writing_band_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    writing_band_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    writing_expired: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    speaking_band: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="in_progress"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="mock_sessions")


class VocabularyItem(Base):
    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    word: Mapped[str] = mapped_column(String(120), nullable=False)
    meaning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    example: Mapped[str] = mapped_column(Text, nullable=False, default="")
    topic: Mapped[str] = mapped_column(String(80), nullable=False, default="general")
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    next_review: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="vocabulary")

    __table_args__ = (
        UniqueConstraint("user_id", "word", name="uq_user_word"),
    )


class Feedback(Base):
    """In-app feedback from a signed-in learner (Phase 4 feedback loop).

    No third-party service and no email is involved: feedback is stored
    in-app and triaged by an admin (see routers/feedback_loop.py).
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="feedback")
