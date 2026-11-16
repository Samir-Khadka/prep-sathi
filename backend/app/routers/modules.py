"""Module catalogue: the four IELTS modules with their real format.

Phase 1 ships the format information and empty practice screens only.
Practice content (original tests, prompts, cue cards) arrives in Phase 2.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import ModuleInfo

router = APIRouter(prefix="/modules", tags=["modules"])

MODULES: dict[str, dict] = {
    "listening": {
        "name": "Listening",
        "time_minutes": "About 30 minutes",
        "questions": "40 questions in 4 parts",
        "description": (
            "Four recordings you hear once only: an everyday conversation, "
            "an everyday monologue, an educational discussion, and an "
            "academic lecture. Question types include multiple choice, "
            "matching, map and diagram labelling, and form, note, table "
            "and sentence completion."
        ),
        "status": "Practice content arrives in Phase 2 — original recordings "
        "and questions written to this exact format.",
    },
    "reading": {
        "name": "Reading",
        "time_minutes": "60 minutes",
        "questions": "40 questions in 3 sections",
        "description": (
            "Three long passages with questions such as True / False / "
            "Not Given, matching headings, matching information, multiple "
            "choice, and sentence and summary completion. Academic uses "
            "academic texts; General Training uses everyday and workplace "
            "texts."
        ),
        "status": "Practice content arrives in Phase 2 — original passages "
        "with evidence-linked explanations for every answer.",
    },
    "writing": {
        "name": "Writing",
        "time_minutes": "60 minutes",
        "questions": "2 tasks",
        "description": (
            "Task 1 (at least 150 words, about 20 minutes): Academic "
            "describes a chart, graph, table or process; General Training "
            "writes a letter. Task 2 (at least 250 words, about 40 "
            "minutes) is an essay in both tracks and carries more weight. "
            "Judged on task achievement, coherence and cohesion, lexical "
            "resource, and grammatical range and accuracy."
        ),
        "status": "Practice content arrives in Phase 2 — original prompts "
        "with model answers and feedback by the four official criteria.",
    },
    "speaking": {
        "name": "Speaking",
        "time_minutes": "11–14 minutes",
        "questions": "3 parts",
        "description": (
            "Part 1: short interview questions. Part 2: a topic card with "
            "1 minute of preparation and a 1–2 minute talk. Part 3: a "
            "follow-up discussion. Judged on fluency and coherence, "
            "lexical resource, grammatical range and accuracy, and "
            "pronunciation."
        ),
        "status": "Practice content arrives in Phase 2 — topic sets, cue "
        "cards, and on-device recording with playback.",
    },
}


@router.get("", response_model=list[ModuleInfo])
def list_modules() -> list[ModuleInfo]:
    return [
        ModuleInfo(slug=slug, **info) for slug, info in MODULES.items()
    ]


@router.get("/{slug}", response_model=ModuleInfo)
def get_module(slug: str) -> ModuleInfo:
    info = MODULES.get(slug)
    if info is None:
        raise HTTPException(status_code=404, detail="Unknown module")
    return ModuleInfo(slug=slug, **info)
