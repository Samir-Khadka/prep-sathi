"""Raw-score to band conversion for Listening and Reading.

Tables are the widely published approximations (IDP / British Council /
Cambridge guidance). Exact boundaries shift slightly between real test
versions, which is why every band the product shows is labelled a
practice estimate, never an official score. Band 0 is reserved for
"did not attempt", so a raw score of 0-2 maps to band 1.0.
"""
from __future__ import annotations

import math
import re

# Each table is a list of (minimum raw score for this band, band),
# highest band first. raw_to_band returns the first band whose minimum
# the raw score reaches.
LISTENING_TABLE: list[tuple[int, float]] = [
    (39, 9.0),
    (37, 8.5),
    (35, 8.0),
    (32, 7.5),
    (30, 7.0),
    (26, 6.5),
    (23, 6.0),
    (18, 5.5),
    (16, 5.0),
    (13, 4.5),
    (10, 4.0),
    (8, 3.5),
    (6, 3.0),
    (4, 2.5),
    (3, 2.0),
    (0, 1.0),
]

READING_ACADEMIC_TABLE: list[tuple[int, float]] = [
    (39, 9.0),
    (37, 8.5),
    (35, 8.0),
    (33, 7.5),
    (30, 7.0),
    (27, 6.5),
    (23, 6.0),
    (19, 5.5),
    (15, 5.0),
    (13, 4.5),
    (10, 4.0),
    (8, 3.5),
    (6, 3.0),
    (4, 2.5),
    (3, 2.0),
    (0, 1.0),
]

READING_GT_TABLE: list[tuple[int, float]] = [
    (40, 9.0),
    (39, 8.5),
    (37, 8.0),
    (36, 7.5),
    (34, 7.0),
    (32, 6.5),
    (30, 6.0),
    (27, 5.5),
    (23, 5.0),
    (19, 4.5),
    (15, 4.0),
    (12, 3.5),
    (9, 3.0),
    (6, 2.5),
    (4, 2.0),
    (3, 1.5),
    (0, 1.0),
]

TABLES: dict[str, list[tuple[int, float]]] = {
    "listening": LISTENING_TABLE,
    "reading-academic": READING_ACADEMIC_TABLE,
    "reading-general": READING_GT_TABLE,
}

BAND_LABEL = "practice estimate, not an official score"

# Timed-mode limits (seconds). Listening: 30 minutes for the recordings
# plus 2 minutes to check answers (computer-delivered). Reading: 60
# minutes, no transfer time.
LISTENING_TIME_LIMIT_SECONDS = 1920
READING_TIME_LIMIT_SECONDS = 3600
# Grace after the limit before a timed submit is refused.
SUBMIT_GRACE_SECONDS = 60


def raw_to_band(table: list[tuple[int, float]], raw: int) -> float:
    """Convert a raw score out of 40 to an estimated band."""
    raw = max(0, min(40, int(raw)))
    for minimum, band in table:
        if raw >= minimum:
            return band
    return 1.0  # Unreachable: the last row starts at 0.


def listening_band(raw: int) -> float:
    return raw_to_band(LISTENING_TABLE, raw)


def reading_band(track: str, raw: int) -> float:
    if track == "general":
        return raw_to_band(READING_GT_TABLE, raw)
    return raw_to_band(READING_ACADEMIC_TABLE, raw)


def overall_band(bands: list[float]) -> float:
    """Average four section bands with IELTS rounding: .25 rounds UP to
    the next half band, .75 rounds UP to the next whole band."""
    avg = sum(bands) / len(bands)
    return math.floor(avg * 2 + 0.5) / 2


_WS_RE = re.compile(r"\s+")


def normalize_short_answer(value: str) -> str:
    """Normalise a short/completion answer for comparison: lowercase,
    collapse whitespace, straighten quotes and dashes, strip a trailing
    full stop."""
    text = value.strip().lower()
    text = text.replace("\u2019", "'").replace("\u2013", "-").replace(
        "\u2014", "-"
    )
    text = _WS_RE.sub(" ", text)
    return text.rstrip(".").strip()


def short_answer_matches(given: str, accepted: list[str]) -> bool:
    return normalize_short_answer(given) in {
        normalize_short_answer(a) for a in accepted
    }
