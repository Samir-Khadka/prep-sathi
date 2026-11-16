"""Pydantic schemas for the PrepSathi API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

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
