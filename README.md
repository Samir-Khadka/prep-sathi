# PrepSathi

Free IELTS-format practice for Nepali phone-first learners — original
practice material, honest band estimates.

**Status: Phase 2 MVP (v0.2.0).** Listening and Reading timed tests
with automatic scoring and band estimates, Writing guided practice with
model answers, Speaking sets with on-device recording, vocabulary
flashcards with spaced-repetition review and a 200-word starter deck,
and a progress dashboard with section trends and target-band tracking.
Nothing here is copied from Cambridge books or any published test —
all practice material is original and written to the official IELTS
format. Listening audio is pending real recordings (no TTS was
available); transcripts are shown instead.

## What it is

- **Four modules** — Listening (~30 min, 40 questions), Reading
  (60 min, 40 questions), Writing (60 min, 2 tasks), Speaking
  (11–14 min, 3 parts) — with the real timings, question types and
  scoring criteria from the official format.
- **Timed mocks and honest bands** — section bands reported separately,
  overall band averaged the official way. Every band shown is labelled
  a *practice estimate, not an official score*.
- **Vocabulary** — spaced-repetition flashcards built from the learner's
  own mistakes.
- **Progress dashboard** — attempts, section trends, words due, and a
  target band (for example 6.5 overall with 6.0 in Writing) counting
  down to the learner's test date.
- **Official resources hub** — links out to the IELTS partners' own
  free material (IELTS.org samples, British Council IELTS Ready and
  familiarisation test, IDP resources). PrepSathi never mirrors or
  re-hosts their files.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React + Vite + TypeScript, built as a PWA (manifest + service worker, offline shell cache) |
| Backend | FastAPI (Python), REST API |
| Database | PostgreSQL on Neon (free tier) in production, SQLite for local dev |
| Auth | Email + password, PBKDF2 hashing, JWT sessions (7 days) |
| Hosting | Free tiers — Render static site (frontend) + Render web service (backend) |

## Run it locally

```bash
# Backend (http://localhost:8000)
cd backend
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
cp .env.example .env        # optional: set DATABASE_URL, JWT secret
../.venv/bin/uvicorn app.main:app --reload

# Frontend (http://localhost:5173)
cd frontend
npm install --ignore-scripts
npm run dev                 # talks to the API at VITE_API_URL (default localhost:8000)
```

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest tests/ -q
cd frontend && npm run typecheck && npm run build
```

## Deploy

`render.yaml` defines the free-tier deploy: a static site for the
frontend and a web service for the backend (Postgres via Neon —
`DATABASE_URL` is set in the Render dashboard, never in this repo).

**Note (Nov 2026):** Render's free web services are suspended until
1 Dec (750 free instance hours exhausted across the workspace). The
backend will not run on Render until then; the frontend static site is
unaffected. Until 1 Dec, run the backend locally as above.

## Design

Light premium only — warm ivory `#FAF6ED`, royal violet `#5B3EA8`,
antique gold. No black backgrounds.

## Decisions left for Samir (see DECISIONS.md)

Product name (PrepSathi is the working name), HashRouter vs
BrowserRouter, Neon provisioning, Listening audio recordings, Google
sign-in, and the vocabulary review schedule.
