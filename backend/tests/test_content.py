"""Tests for the Phase 2 practice content: counts, structure, and the
guarantee that public views never leak answers (spec sections 2 and 5).
"""
from __future__ import annotations

import json

from app.content import ContentStore


def _find_forbidden_keys(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ("answer", "answers"):
                found.append(key)
            found.extend(_find_forbidden_keys(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_forbidden_keys(item))
    return found


def _find_keys(obj: object, wanted: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in wanted:
                found.append(key)
            found.extend(_find_keys(value, wanted))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_keys(item, wanted))
    return found


def test_listening_counts() -> None:
    store = ContentStore()
    assert len(store.listening_tests) == 8
    for test in store.listening_tests:
        questions = [q for part in test["parts"] for q in part["questions"]]
        assert len(questions) == 40
        assert [q["no"] for q in questions] == list(range(1, 41))
        assert all(part["audio_url"] is None for part in test["parts"])
        assert all(part["audio_note"].strip() for part in test["parts"])


def test_reading_counts() -> None:
    store = ContentStore()
    assert len(store.reading_tests) == 8
    tracks = [t["track"] for t in store.reading_tests]
    assert tracks.count("academic") == 6
    assert tracks.count("general") == 2
    for test in store.reading_tests:
        questions = [q for p in test["passages"] for q in p["questions"]]
        assert len(questions) == 40
        assert [q["no"] for q in questions] == list(range(1, 41))


def test_writing_counts() -> None:
    store = ContentStore()
    assert len(store.writing_prompts) == 30
    combos = {(p["track"], p["task"]) for p in store.writing_prompts}
    assert combos == {
        ("academic", 1), ("academic", 2), ("general", 1), ("general", 2),
    }
    expected = {
        ("academic", 1): 8,
        ("academic", 2): 8,
        ("general", 1): 7,
        ("general", 2): 7,
    }
    for track, task in combos:
        count = sum(
            1 for p in store.writing_prompts
            if p["track"] == track and p["task"] == task
        )
        assert count == expected[(track, task)], (track, task, count)


def test_speaking_counts() -> None:
    store = ContentStore()
    assert len(store.speaking_sets) == 20


def test_vocabulary_counts() -> None:
    store = ContentStore()
    assert len(store.vocabulary_deck) == 350
    words = [w["word"].strip().lower() for w in store.vocabulary_deck]
    assert len(set(words)) == 350


def test_public_listening_hides_answers() -> None:
    store = ContentStore()
    for test in store.listening_tests:
        public = store.public_listening(test)
        assert _find_forbidden_keys(public) == []
        assert _find_keys(public, {"explanation", "evidence"}) == []
        # Transcript stays visible (audio is pending).
        assert all(part["transcript"].strip() for part in public["parts"])


def test_public_reading_hides_answers() -> None:
    store = ContentStore()
    for test in store.reading_tests:
        public = store.public_reading(test)
        assert _find_forbidden_keys(public) == []
        assert _find_keys(public, {"explanation", "evidence"}) == []


def test_public_writing_hides_model_answer() -> None:
    store = ContentStore()
    for prompt in store.writing_prompts:
        public = store.public_writing_prompt(prompt)
        assert "model_answer" not in public
        assert "commentary" not in public


def test_content_files_are_valid_json() -> None:
    from app.content import CONTENT_DIR

    for name in (
        "listening_tests.json",
        "reading_tests.json",
        "writing_prompts.json",
        "speaking_sets.json",
        "vocabulary_deck.json",
    ):
        with (CONTENT_DIR / name).open(encoding="utf-8") as f:
            json.load(f)
