"""Configuration for the PrepSathi backend.

Everything comes from the environment so no secret ever lives in code.
Local development uses SQLite; set DATABASE_URL to a Postgres URL
(for example a free Neon database) for deployment.
"""
from __future__ import annotations

import os

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL", "sqlite:///./prepsathi.db"
)
# HS256 signing secret for JWTs. The default is a development placeholder
# only — set PREPSATHI_JWT_SECRET to a long random value in production.
JWT_SECRET: str = os.environ.get(
    "PREPSATHI_JWT_SECRET", "dev-only-placeholder-change-me-in-production"
)
JWT_ALGORITHM: str = "HS256"
# JWTs live 7 days, matching the FitTrack pattern Samir already uses.
JWT_EXPIRE_DAYS: int = int(os.environ.get("JWT_EXPIRE_DAYS", "7"))

CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
