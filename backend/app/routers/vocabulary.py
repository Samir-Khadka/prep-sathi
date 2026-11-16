"""Vocabulary flashcards with spaced-repetition review.

Phase 2 adds the study flow: due items, review (correct grows the
interval, wrong resets it), and a starter-deck seed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..content import ContentStore
from ..database import get_db
from ..deps import get_current_user
from ..models import User, VocabularyItem
from ..schemas import (
    SeedResponse,
    VocabularyCreate,
    VocabularyOut,
    VocabularyReviewRequest,
)

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])

MAX_INTERVAL_DAYS = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/due", response_model=list[VocabularyOut])
def due_words(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VocabularyOut]:
    return (
        db.query(VocabularyItem)
        .filter(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.next_review <= _now(),
        )
        .order_by(VocabularyItem.next_review.asc())
        .limit(50)
        .all()
    )


@router.post("/seed", response_model=SeedResponse, status_code=201)
def seed_starter_deck(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeedResponse:
    """Add the 200-word starter deck, skipping words already in the
    learner's list. Safe to call twice."""
    try:
        deck = ContentStore().vocabulary_deck
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Vocabulary deck is not available yet"
        ) from exc
    existing = {
        row.word
        for row in db.query(VocabularyItem.word)
        .filter(VocabularyItem.user_id == current_user.id)
        .all()
    }
    added = 0
    skipped = 0
    for entry in deck:
        word = entry["word"].strip().lower()
        if word in existing:
            skipped += 1
            continue
        db.add(
            VocabularyItem(
                user_id=current_user.id,
                word=word,
                meaning=entry["meaning"].strip(),
                example=entry["example"].strip(),
                topic=entry["topic"].strip() or "general",
            )
        )
        existing.add(word)
        added += 1
    db.commit()
    return SeedResponse(added=added, skipped=skipped)


@router.post("/{item_id}/review", response_model=VocabularyOut)
def review_word(
    item_id: int,
    payload: VocabularyReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VocabularyOut:
    item = (
        db.query(VocabularyItem)
        .filter(
            VocabularyItem.id == item_id,
            VocabularyItem.user_id == current_user.id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Word not found")
    if payload.correct:
        item.interval_days = min(item.interval_days * 2, MAX_INTERVAL_DAYS)
    else:
        item.interval_days = 1
    item.next_review = _now() + timedelta(days=item.interval_days)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[VocabularyOut])
def list_vocabulary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[VocabularyOut]:
    return (
        db.query(VocabularyItem)
        .filter(VocabularyItem.user_id == current_user.id)
        .order_by(VocabularyItem.created_at.desc())
        .limit(500)
        .all()
    )


@router.post("", response_model=VocabularyOut, status_code=201)
def add_word(
    payload: VocabularyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VocabularyOut:
    existing = (
        db.query(VocabularyItem)
        .filter(
            VocabularyItem.user_id == current_user.id,
            VocabularyItem.word == payload.word.strip().lower(),
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409, detail="This word is already in your list"
        )
    item = VocabularyItem(
        user_id=current_user.id,
        word=payload.word.strip().lower(),
        meaning=payload.meaning.strip(),
        topic=payload.topic.strip() or "general",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_word(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    item = (
        db.query(VocabularyItem)
        .filter(
            VocabularyItem.id == item_id,
            VocabularyItem.user_id == current_user.id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Word not found")
    db.delete(item)
    db.commit()
