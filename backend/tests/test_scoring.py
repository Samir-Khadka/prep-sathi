"""Tests for the raw-score to band conversion (spec section 1)."""
from __future__ import annotations

import pytest

from app.scoring import (
    READING_ACADEMIC_TABLE,
    READING_GT_TABLE,
    LISTENING_TABLE,
    normalize_short_answer,
    overall_band,
    raw_to_band,
    short_answer_matches,
)


@pytest.mark.parametrize(
    "raw,band",
    [
        (40, 9.0), (39, 9.0), (38, 8.5), (37, 8.5), (36, 8.0), (35, 8.0),
        (34, 7.5), (32, 7.5), (31, 7.0), (30, 7.0), (29, 6.5), (26, 6.5),
        (25, 6.0), (23, 6.0), (22, 5.5), (18, 5.5), (17, 5.0), (16, 5.0),
        (15, 4.5), (13, 4.5), (12, 4.0), (10, 4.0), (9, 3.5), (8, 3.5),
        (7, 3.0), (6, 3.0), (5, 2.5), (4, 2.5), (3, 2.0), (2, 1.0),
        (1, 1.0), (0, 1.0),
    ],
)
def test_listening_table(raw: int, band: float) -> None:
    assert raw_to_band(LISTENING_TABLE, raw) == band


@pytest.mark.parametrize(
    "raw,band",
    [
        (40, 9.0), (39, 9.0), (38, 8.5), (37, 8.5), (36, 8.0), (35, 8.0),
        (34, 7.5), (33, 7.5), (32, 7.0), (30, 7.0), (29, 6.5), (27, 6.5),
        (26, 6.0), (23, 6.0), (22, 5.5), (19, 5.5), (18, 5.0), (15, 5.0),
        (14, 4.5), (13, 4.5), (12, 4.0), (10, 4.0), (9, 3.5), (8, 3.5),
        (7, 3.0), (6, 3.0), (5, 2.5), (4, 2.5), (3, 2.0), (2, 1.0),
        (0, 1.0),
    ],
)
def test_reading_academic_table(raw: int, band: float) -> None:
    assert raw_to_band(READING_ACADEMIC_TABLE, raw) == band


@pytest.mark.parametrize(
    "raw,band",
    [
        (40, 9.0), (39, 8.5), (38, 8.0), (37, 8.0), (36, 7.5), (35, 7.0),
        (34, 7.0), (33, 6.5), (32, 6.5), (31, 6.0), (30, 6.0), (29, 5.5),
        (27, 5.5), (26, 5.0), (23, 5.0), (22, 4.5), (19, 4.5), (18, 4.0),
        (15, 4.0), (14, 3.5), (12, 3.5), (11, 3.0), (9, 3.0), (8, 2.5),
        (6, 2.5), (5, 2.0), (4, 2.0), (3, 1.5), (2, 1.0), (0, 1.0),
    ],
)
def test_reading_gt_table(raw: int, band: float) -> None:
    assert raw_to_band(READING_GT_TABLE, raw) == band


def test_raw_clamped() -> None:
    assert raw_to_band(LISTENING_TABLE, 41) == 9.0
    assert raw_to_band(LISTENING_TABLE, -5) == 1.0


def test_same_raw_differs_by_track() -> None:
    # 30/40 is band 7.0 on Academic Reading but 6.0 on General Training.
    assert raw_to_band(READING_ACADEMIC_TABLE, 30) == 7.0
    assert raw_to_band(READING_GT_TABLE, 30) == 6.0


@pytest.mark.parametrize(
    "bands,expected",
    [
        ([6.5, 6.5, 6.0, 6.0], 6.5),  # 6.25 rounds UP to 6.5
        ([7.0, 7.0, 7.0, 6.0], 7.0),  # 6.75 rounds UP to 7.0
        ([6.0, 6.0, 6.0, 6.0], 6.0),
        ([9.0, 9.0, 9.0, 9.0], 9.0),
        ([7.0, 6.5, 6.0, 6.5], 6.5),  # 6.5 exactly
        ([5.5, 5.5, 5.0, 5.0], 5.5),  # 5.25 rounds UP to 5.5
    ],
)
def test_overall_band_rounding(bands: list[float], expected: float) -> None:
    assert overall_band(bands) == expected


def test_normalize_short_answer() -> None:
    assert normalize_short_answer("  Hello   World. ") == "hello world"
    assert normalize_short_answer("10.30") == "10.30"
    assert normalize_short_answer("Water vapour.") == "water vapour"


def test_short_answer_matches() -> None:
    assert short_answer_matches("10:30", ["10.30", "10:30", "half past ten"])
    assert short_answer_matches("Half Past Ten.", ["10.30", "half past ten"])
    assert not short_answer_matches("11.30", ["10.30", "half past ten"])
    assert not short_answer_matches("", ["10.30"])
