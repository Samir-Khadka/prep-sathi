"""In-app feedback loop (Phase 4).

Learners send feedback from inside the app; admins triage it in-app.
No third-party service and no email is involved.

Admin gating: the ADMIN_EMAILS environment variable holds a
comma-separated list of admin email addresses. It is read on every
request so tests (and deploys) can set it without a restart. An empty
list means no admin access: every admin call returns 403.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Feedback, User
from ..schemas import FeedbackCreate, FeedbackOut, FeedbackUpdate

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _admin_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in os.environ.get("ADMIN_EMAILS", "").split(",")
        if email.strip()
    }


def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.email.lower() not in _admin_emails():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def _out(row: Feedback) -> FeedbackOut:
    return FeedbackOut.model_validate(row)


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    row = Feedback(
        user_id=current_user.id,
        category=payload.category,
        message=payload.message.strip(),
        page=payload.page.strip() if payload.page else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.get("", response_model=list[FeedbackOut])
def list_own_feedback(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FeedbackOut]:
    rows = (
        db.query(Feedback)
        .filter(Feedback.user_id == current_user.id)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
        .all()
    )
    return [_out(row) for row in rows]


@router.get("/admin", response_model=list[FeedbackOut])
def list_all_feedback(
    resolved: bool | None = Query(default=None),
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> list[FeedbackOut]:
    query = db.query(Feedback)
    if resolved is not None:
        query = query.filter(Feedback.resolved == resolved)
    rows = query.order_by(
        Feedback.created_at.desc(), Feedback.id.desc()
    ).all()
    return [_out(row) for row in rows]


@router.patch("/admin/{feedback_id}", response_model=FeedbackOut)
def set_resolved(
    feedback_id: int,
    payload: FeedbackUpdate,
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    row = db.get(Feedback, feedback_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )
    row.resolved = payload.resolved
    db.commit()
    db.refresh(row)
    return _out(row)
