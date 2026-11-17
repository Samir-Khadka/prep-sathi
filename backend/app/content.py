"""Original practice content, loaded from JSON and validated on load.

All content is written for this product; no Cambridge material is used.
Files live in backend/app/content/. The loader validates structure,
question numbering, answer ranges and non-empty explanations, so a bad
content file fails loudly at startup and in tests instead of silently
serving a broken test.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent / "content"

_VALID_TFNG = {"TRUE", "FALSE", "NOT GIVEN"}

# Phase 5.2: a Listening part may have no recording yet (null) or a
# real recording served from /static/audio/listening/<TEST>/part<N>.mp3.
# The URL must name the test and part it belongs to — a mismatched URL
# is a content error, not a silent wrong-audio bug.
_AUDIO_URL_RE = re.compile(r"^/static/audio/listening/(L[1-8])/part([1-4])\.mp3$")


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


def _non_empty(value: object, where: str) -> str:
    _require(isinstance(value, str) and value.strip() != "", f"{where}: empty text")
    return str(value)


def _validate_question(q: dict, where: str) -> None:
    _require(isinstance(q.get("no"), int), f"{where}: question has no number")
    _require(q["type"] in ("short", "mcq", "tfng"), f"{where}: bad type {q.get('type')!r}")
    _non_empty(q.get("prompt"), f"{where}: empty prompt")
    _non_empty(q.get("explanation"), f"{where}: missing explanation")
    _non_empty(q.get("evidence"), f"{where}: missing evidence")
    if q["type"] == "short":
        answers = q.get("answers")
        _require(
            isinstance(answers, list) and len(answers) >= 1
            and all(isinstance(a, str) and a.strip() for a in answers),
            f"{where}: short question needs a non-empty answers list",
        )
    elif q["type"] == "mcq":
        options = q.get("options")
        _require(
            isinstance(options, list) and len(options) >= 2
            and all(isinstance(o, str) and o.strip() for o in options),
            f"{where}: mcq needs at least 2 non-empty options",
        )
        _require(
            isinstance(q.get("answer"), int) and 0 <= q["answer"] < len(options),
            f"{where}: mcq answer index out of range",
        )
    elif q["type"] == "tfng":
        _require(
            isinstance(q.get("answer"), str)
            and q["answer"].upper() in _VALID_TFNG,
            f"{where}: tfng answer must be TRUE, FALSE or NOT GIVEN",
        )


def _check_numbering(questions: list[dict], where: str) -> None:
    numbers = [q["no"] for q in questions]
    _require(
        numbers == list(range(1, len(numbers) + 1)),
        f"{where}: questions must be numbered 1..{len(numbers)} in order, "
        f"got {numbers[:5]}...",
    )


def _valid_audio_url(value: object, test_id: object, part_no: int) -> bool:
    """Null means "no recording yet"; a string must be the exact
    /static/audio/listening/<TEST>/part<N>.mp3 path for this test/part."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    match = _AUDIO_URL_RE.match(value)
    return bool(match and match.group(1) == test_id and int(match.group(2)) == part_no)


def _validate_listening(test: dict) -> None:
    where = f"listening {test.get('id')}"
    parts = test.get("parts")
    _require(isinstance(parts, list) and len(parts) == 4, f"{where}: need 4 parts")
    all_questions: list[dict] = []
    for i, part in enumerate(parts, start=1):
        pwhere = f"{where} part {i}"
        _require(part.get("part") == i, f"{pwhere}: part number mismatch")
        _non_empty(part.get("title"), pwhere)
        _non_empty(part.get("setting"), pwhere)
        _non_empty(part.get("transcript"), pwhere)
        _require(part.get("audio_url") is None or _valid_audio_url(
            part.get("audio_url"), test.get("id"), i),
            f"{pwhere}: audio_url must be null or "
            f"/static/audio/listening/<test>/part<1-4>.mp3 for this test/part")
        _non_empty(part.get("audio_note"), pwhere)
        questions = part.get("questions")
        _require(isinstance(questions, list) and len(questions) == 10,
                 f"{pwhere}: need 10 questions")
        for q in questions:
            _validate_question(q, pwhere)
        all_questions.extend(questions)
    _require(len(all_questions) == 40, f"{where}: need 40 questions total")
    _check_numbering(all_questions, where)


def _validate_reading(test: dict) -> None:
    where = f"reading {test.get('id')}"
    _require(test.get("track") in ("academic", "general"), f"{where}: bad track")
    passages = test.get("passages")
    _require(isinstance(passages, list) and len(passages) == 3,
             f"{where}: need 3 passages/sections")
    all_questions: list[dict] = []
    for i, passage in enumerate(passages, start=1):
        pwhere = f"{where} section {i}"
        _require(passage.get("section") == i, f"{pwhere}: section number mismatch")
        _non_empty(passage.get("title"), pwhere)
        text = _non_empty(passage.get("text"), pwhere)
        questions = passage.get("questions")
        _require(isinstance(questions, list) and len(questions) >= 1,
                 f"{pwhere}: need questions")
        for q in questions:
            _validate_question(q, pwhere)
            evidence = q["evidence"]
            _require(
                evidence.strip() in text or evidence.strip().lower() in text.lower(),
                f"{pwhere} q{q['no']}: evidence is not from the passage text",
            )
        all_questions.extend(questions)
    _require(len(all_questions) == 40, f"{where}: need 40 questions total")
    _check_numbering(all_questions, where)


def _validate_writing(prompt: dict) -> None:
    where = f"writing {prompt.get('id')}"
    _require(prompt.get("track") in ("academic", "general"), f"{where}: bad track")
    _require(prompt.get("task") in (1, 2), f"{where}: bad task")
    _non_empty(prompt.get("title"), where)
    _non_empty(prompt.get("prompt"), where)
    expected_min = 150 if prompt["task"] == 1 else 250
    _require(prompt.get("min_words") == expected_min,
             f"{where}: min_words must be {expected_min}")
    _non_empty(prompt.get("model_answer"), where)
    _non_empty(prompt.get("commentary"), where)


def _validate_speaking(entry: dict) -> None:
    where = f"speaking {entry.get('id')}"
    _non_empty(entry.get("topic"), where)
    _require(isinstance(entry.get("part1"), list) and len(entry["part1"]) >= 3,
             f"{where}: need at least 3 Part 1 questions")
    part2 = entry.get("part2")
    _require(isinstance(part2, dict), f"{where}: missing part2")
    _non_empty(part2.get("cue"), where)
    _require(isinstance(part2.get("points"), list) and len(part2["points"]) >= 3,
             f"{where}: need at least 3 Part 2 points")
    _require(part2.get("prep_seconds") == 60, f"{where}: prep must be 60s")
    _require(part2.get("talk_seconds") == 120, f"{where}: talk must be 120s")
    _require(isinstance(entry.get("part3"), list) and len(entry["part3"]) >= 3,
             f"{where}: need at least 3 Part 3 questions")
    _non_empty(entry.get("sample_answer"), where)


def _validate_vocabulary(words: list[dict]) -> None:
    seen: set[str] = set()
    for w in words:
        word = _non_empty(w.get("word"), "vocabulary").strip().lower()
        _require(word not in seen, f"vocabulary: duplicate word {word!r}")
        seen.add(word)
        _non_empty(w.get("meaning"), f"vocabulary {word}")
        _non_empty(w.get("example"), f"vocabulary {word}")
        _non_empty(w.get("topic"), f"vocabulary {word}")


class ContentStore:
    """All Phase 2 practice content, loaded and validated once."""

    def __init__(self, directory: Path = CONTENT_DIR) -> None:
        self._directory = directory
        self._load_all(directory)

    def _load_all(self, directory: Path) -> None:
        self.listening_tests = self._load(directory / "listening_tests.json", "tests")
        for test in self.listening_tests:
            _validate_listening(test)
        self.reading_tests = self._load(directory / "reading_tests.json", "tests")
        for test in self.reading_tests:
            _validate_reading(test)
        self.writing_prompts = self._load(directory / "writing_prompts.json", "prompts")
        for prompt in self.writing_prompts:
            _validate_writing(prompt)
        self.speaking_sets = self._load(directory / "speaking_sets.json", "sets")
        for entry in self.speaking_sets:
            _validate_speaking(entry)
        self.vocabulary_deck = self._load(directory / "vocabulary_deck.json", "words")
        _validate_vocabulary(self.vocabulary_deck)

    def reload(self) -> None:
        """Re-read every content file from disk and re-validate.

        Used after an admin audio upload changes listening_tests.json,
        so the new audio_url is served without a restart. Raises
        ValueError if the reloaded content is invalid — the caller
        should only call this after validating the change itself.
        """
        self._load_all(self._directory)

    @staticmethod
    def _load(path: Path, key: str) -> list:
        _require(path.exists(), f"content file missing: {path}")
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        _require(isinstance(data, dict) and isinstance(data.get(key), list),
                 f"{path.name}: expected an object with a {key!r} list")
        return data[key]

    # -- lookups -------------------------------------------------------
    def listening(self, test_id: str) -> dict | None:
        return next((t for t in self.listening_tests if t["id"] == test_id), None)

    def reading(self, test_id: str) -> dict | None:
        return next((t for t in self.reading_tests if t["id"] == test_id), None)

    def writing(self, prompt_id: str) -> dict | None:
        return next((p for p in self.writing_prompts if p["id"] == prompt_id), None)

    def speaking(self, set_id: str) -> dict | None:
        return next((s for s in self.speaking_sets if s["id"] == set_id), None)

    # -- public views (answers stripped) -------------------------------
    @staticmethod
    def _public_question(q: dict) -> dict:
        out: dict = {"no": q["no"], "type": q["type"], "prompt": q["prompt"]}
        if q["type"] == "mcq":
            out["options"] = q["options"]
        return out

    def public_listening(self, test: dict) -> dict:
        return {
            "id": test["id"],
            "title": test["title"],
            "parts": [
                {
                    "part": part["part"],
                    "title": part["title"],
                    "setting": part["setting"],
                    "transcript": part["transcript"],
                    "audio_url": part["audio_url"],
                    "audio_note": part["audio_note"],
                    "questions": [self._public_question(q) for q in part["questions"]],
                }
                for part in test["parts"]
            ],
        }

    def public_reading(self, test: dict) -> dict:
        return {
            "id": test["id"],
            "track": test["track"],
            "title": test["title"],
            "passages": [
                {
                    "section": passage["section"],
                    "title": passage["title"],
                    "text": passage["text"],
                    "questions": [self._public_question(q) for q in passage["questions"]],
                }
                for passage in test["passages"]
            ],
        }

    def public_writing_prompt(self, prompt: dict) -> dict:
        return {
            "id": prompt["id"],
            "track": prompt["track"],
            "task": prompt["task"],
            "title": prompt["title"],
            "prompt": prompt["prompt"],
            "min_words": prompt["min_words"],
            "suggested_minutes": prompt["suggested_minutes"],
        }
