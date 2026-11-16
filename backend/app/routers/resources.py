"""Official free resources hub.

PrepSathi links out to the IELTS partners' own free material — it never
mirrors or re-hosts their files, and it contains no Cambridge book
content. URLs were verified live in November 2026.
"""
from __future__ import annotations

from fastapi import APIRouter

from ..schemas import ResourceLink

router = APIRouter(prefix="/resources", tags=["resources"])

OFFICIAL_RESOURCES: list[dict] = [
    {
        "title": "IELTS.org — free sample questions",
        "url": "https://ielts.org",
        "description": (
            "Sample tasks for all four skills, Academic and General "
            "Training, with answer keys, listening transcripts and writing "
            "responses with examiner comments. The format reference — "
            "check the real thing here."
        ),
        "provider": "IELTS partners",
    },
    {
        "title": "British Council — IELTS Ready (free)",
        "url": "https://takeielts.britishcouncil.org/take-ielts/prepare/ielts-ready",
        "description": (
            "A 25-minute Express Mock and a 50-minute Mini Mock with "
            "personalised feedback, plus full practice tests, short "
            "courses and live webinars. Free with sign-up."
        ),
        "provider": "British Council",
    },
    {
        "title": "British Council — familiarisation test",
        "url": "https://takeielts.britishcouncil.org/en-gb/prepare",
        "description": (
            "Full-length Listening, Reading and Writing on the real "
            "computer-test screens, so the test-day interface is not a "
            "surprise. Start here before your first full mock."
        ),
        "provider": "British Council",
    },
    {
        "title": "IDP — familiarisation tests",
        "url": "https://ielts.idp.com/about/ielts-familiarisation-tests",
        "description": (
            "Practise highlighting, navigation, scrolling and answer "
            "editing on the computer test screens, without time pressure."
        ),
        "provider": "IDP",
    },
    {
        "title": "IDP — band scores explained",
        "url": "https://ielts.idp.com/srilanka/results/scores",
        "description": (
            "How the 0–9 band scale works, what each band means, and how "
            "the overall band is calculated from the four section bands."
        ),
        "provider": "IDP",
    },
]


@router.get("", response_model=list[ResourceLink])
def list_resources() -> list[ResourceLink]:
    return [ResourceLink(**item) for item in OFFICIAL_RESOURCES]
