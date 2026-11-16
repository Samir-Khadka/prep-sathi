"""PrepSathi API — FastAPI backend (Phase 2 MVP).

Free IELTS-format practice for Nepali phone-first learners. All practice
content is original and written to the official format; no Cambridge
copyrighted material is included anywhere. Band scores shown anywhere
are practice estimates, not official scores.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .database import init_db
from .routers import attempts, auth, dashboard, modules, practice, resources, vocabulary


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PrepSathi API",
    description=(
        "Free IELTS-format practice for Nepali phone-first learners. "
        "All practice content is original; band scores shown anywhere "
        "are practice estimates, not official scores."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(resources.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(attempts.router, prefix="/api")
app.include_router(vocabulary.router, prefix="/api")
app.include_router(practice.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "prepsathi", "version": "0.2.0"}
