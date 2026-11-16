"""Progress dashboard: attempts, vocabulary, and target bands.

Progress is computed from attempts, so the dashboard never needs
separate manual entry.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Attempt, User, VocabularyItem
from ..routers.attempts import _out as _attempt_out
from ..routers.practice import latest_bands, overall_estimate
from ..schemas import DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardOut:
    attempts_total = (
        db.query(func.count(Attempt.id))
        .filter(Attempt.user_id == current_user.id)
        .scalar()
        or 0
    )
    by_module_rows = (
        db.query(Attempt.module, func.count(Attempt.id))
        .filter(Attempt.user_id == current_user.id)
        .group_by(Attempt.module)
        .all()
    )
    vocabulary_total = (
        db.query(func.count(VocabularyItem.id))
        .filter(VocabularyItem.user_id == current_user.id)
        .scalar()
        or 0
    )
    vocabulary_due = (
        db.query(func.count(VocabularyItem.id))
        .filter(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.next_review <= datetime.now(timezone.utc),
        )
        .scalar()
        or 0
    )
    recent_rows = (
        db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.created_at.desc())
        .limit(10)
        .all()
    )
    return DashboardOut(
        attempts_total=attempts_total,
        attempts_by_module={module: count for module, count in by_module_rows},
        vocabulary_total=vocabulary_total,
        vocabulary_due=vocabulary_due,
        target_band_overall=current_user.target_band_overall,
        target_band_writing=current_user.target_band_writing,
        latest_band_by_module=latest_bands(db, current_user.id),
        overall_estimate=overall_estimate(db, current_user.id),
        attempts_recent=[_attempt_out(row) for row in recent_rows],
    )
