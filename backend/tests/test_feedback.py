"""Tests for automated Writing feedback (Phase 3, backend only).

The weak fixture is original text written for this test — no Cambridge
material. Calibration is pinned here: every model answer in the
product's content scores an overall low end of 7.0 or above, and the
weak fixture scores an overall high end of 5.5 or below.
"""
from __future__ import annotations

from app.content import ContentStore
from app.feedback import LIMITS, analyse_writing
from tests.conftest import client, user_headers

_STORE = ContentStore()

# Original weak text written for this test: about 115 words (below the
# 250-word minimum for WA-T2-01), one paragraph, repetitive vocabulary,
# near-identical sentence lengths, "very" overuse, "I think" openers.
WEAK_TEXT = (
    "I think free university is good for students in my country today. "
    "I think students need money because university is very expensive for students. "
    "I think poor students cannot pay money for university and they need help. "
    "I think free university is very good because students can study and learn. "
    "Many poor students want jobs but students need money for university study. "
    "I think free university is very important for poor students and all students. "
    "Students need help because university is very hard and very expensive for students. "
    "I think free university is good for students and good for my country today. "
    "Poor students need free university because they need money and they need jobs."
)

CRITERIA = ("task_achievement", "coherence", "lexical", "grammar")


def _is_half_step(value: float) -> bool:
    return abs(value * 2 - round(value * 2)) < 1e-9


def test_feedback_shape_for_model_answer() -> None:
    prompt = _STORE.writing("WA-T2-01")
    assert prompt is not None
    result = analyse_writing(prompt, prompt["model_answer"])
    assert set(result) == {
        "prompt_id",
        "word_count",
        "min_words",
        "meets_minimum",
        "band_low",
        "band_high",
        "band_label",
        "criteria",
        "limits",
    }
    assert result["prompt_id"] == "WA-T2-01"
    # word_count counts alphabetic tokens (the feedback module's
    # definition), not whitespace-split words: "income-based" is two
    # tokens, "420,000" is none.
    assert result["word_count"] == 292
    assert result["min_words"] == 250
    assert result["meets_minimum"] is True
    assert result["band_label"] == "practice estimate, not an official score"
    assert result["limits"] == LIMITS
    assert "cannot judge your ideas" in result["limits"]
    assert set(result["criteria"]) == set(CRITERIA)
    for criterion in result["criteria"].values():
        assert set(criterion) == {"band_low", "band_high", "notes"}
        assert 4.0 <= criterion["band_low"] <= criterion["band_high"] <= 8.0
        assert _is_half_step(criterion["band_low"])
        assert _is_half_step(criterion["band_high"])
        assert 2 <= len(criterion["notes"]) <= 4
        assert all(isinstance(note, str) and note for note in criterion["notes"])
    assert 4.0 <= result["band_low"] <= result["band_high"] <= 8.0
    assert _is_half_step(result["band_low"])
    assert _is_half_step(result["band_high"])


def test_model_answers_score_high() -> None:
    """Every model answer in the product's content lands at 7.0+ low end."""
    for prompt in _STORE.writing_prompts:
        result = analyse_writing(prompt, prompt["model_answer"])
        assert result["meets_minimum"] is True, prompt["id"]
        assert result["band_low"] >= 7.0, (prompt["id"], result)
        assert result["band_high"] <= 8.0, (prompt["id"], result)


def test_weak_fixture_scores_low() -> None:
    prompt = _STORE.writing("WA-T2-01")
    assert prompt is not None
    result = analyse_writing(prompt, WEAK_TEXT)
    assert result["word_count"] == 115
    assert result["min_words"] == 250
    assert result["meets_minimum"] is False
    assert result["band_high"] <= 5.5, result
    assert result["band_low"] < result["band_high"]


def test_word_count_and_minimum_for_task1() -> None:
    prompt = _STORE.writing("WA-T1-01")
    assert prompt is not None
    short = analyse_writing(prompt, "The chart shows three museums. Overall, one grew.")
    assert short["word_count"] == 8
    assert short["min_words"] == 150
    assert short["meets_minimum"] is False
    assert short["band_high"] <= 6.0
    exact = analyse_writing(prompt, " ".join(["word"] * 150))
    assert exact["word_count"] == 150
    assert exact["meets_minimum"] is True


def test_empty_text_is_handled_not_crash() -> None:
    prompt = _STORE.writing("WA-T2-01")
    assert prompt is not None
    result = analyse_writing(prompt, "   ")
    assert result["word_count"] == 0
    assert result["meets_minimum"] is False
    assert result["band_low"] == 4.0


def test_feedback_endpoint_matches_analyse_writing(user_token: dict) -> None:
    prompt = _STORE.writing("WA-T2-01")
    assert prompt is not None
    expected = analyse_writing(prompt, prompt["model_answer"])
    resp = client.post(
        "/api/practice/writing/feedback",
        headers=user_headers(user_token),
        json={"prompt_id": "WA-T2-01", "text": prompt["model_answer"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == expected


def test_feedback_endpoint_weak_text(user_token: dict) -> None:
    resp = client.post(
        "/api/practice/writing/feedback",
        headers=user_headers(user_token),
        json={"prompt_id": "WA-T2-01", "text": WEAK_TEXT},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["band_high"] <= 5.5
    assert body["meets_minimum"] is False


def test_feedback_unknown_prompt_404(user_token: dict) -> None:
    resp = client.post(
        "/api/practice/writing/feedback",
        headers=user_headers(user_token),
        json={"prompt_id": "NOPE-00", "text": "Some text here."},
    )
    assert resp.status_code == 404, resp.text


def test_feedback_empty_text_400(user_token: dict) -> None:
    resp = client.post(
        "/api/practice/writing/feedback",
        headers=user_headers(user_token),
        json={"prompt_id": "WA-T2-01", "text": "   "},
    )
    assert resp.status_code == 400, resp.text


def test_feedback_unauthenticated_401() -> None:
    resp = client.post(
        "/api/practice/writing/feedback",
        json={"prompt_id": "WA-T2-01", "text": "Some text here."},
    )
    assert resp.status_code == 401, resp.text


def test_feedback_does_not_change_submit(user_token: dict) -> None:
    """The existing submit endpoint still behaves as before."""
    headers = user_headers(user_token)
    resp = client.post(
        "/api/practice/writing/submit",
        headers=headers,
        json={"prompt_id": "WA-T1-01", "text": " ".join(["word"] * 160)},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["word_count"] == 160
    assert body["meets_minimum"] is True
    assert "attempt_id" in body
