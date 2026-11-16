"""Attempts: record and list practice/mock attempts.

Phase 1 records attempts only — scoring and band estimates arrive with
the Phase 2 practice content. Any band_estimate recorded here is
labelled in the response as a practice estimate, never an official score.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Attempt, User
from ..schemas import MODULES, AttemptCreate, AttemptOut

router = APIRouter(prefix="/attempts", tags=["attempts"])

BAND_LABEL = "practice estimate, not an official score"


def _out(attempt: Attempt) -> AttemptOut:
    return AttemptOut(
        id=attempt.id,
        module=attempt.module,
        kind=attempt.kind,
        score_raw=attempt.score_raw,
        band_estimate=attempt.band_estimate,
        band_label=BAND_LABEL if attempt.band_estimate is not None else None,
        duration_seconds=attempt.duration_seconds,
        created_at=attempt.created_at,
    )


@router.post("", response_model=AttemptOut, status_code=201)
def record_attempt(
    payload: AttemptCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptOut:
    if payload.module not in MODULES:
        raise HTTPException(status_code=400, detail="Unknown module")
    attempt = Attempt(
        user_id=current_user.id,
        module=payload.module,
        kind=payload.kind,
        score_raw=payload.score_raw,
        band_estimate=payload.band_estimate,
        duration_seconds=payload.duration_seconds,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _out(attempt)


@router.get("", response_model=list[AttemptOut])
def list_attempts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AttemptOut]:
    rows = (
        db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.created_at.desc())
        .limit(100)
        .all()
    )
    return [_out(row) for row in rows]
