"""Vocabulary flashcards with spaced-repetition fields.

Phase 1: add, list, and delete words. The review schedule (interval
growth on correct recall) arrives with the Phase 2 study flow.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User, VocabularyItem
from ..schemas import VocabularyCreate, VocabularyOut

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


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
