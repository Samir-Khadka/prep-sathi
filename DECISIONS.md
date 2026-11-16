# PrepSathi — decisions made during the Phase 1 build, for Samir's
# review after his 24 Nov IELTS sitting. Nothing here is locked; each
# item names the default taken and what would change it.

1. **Product name: PrepSathi (working name).** "Sathi" = companion.
   Changeable at any point before public launch. The name must not use
   "IELTS" or "Cambridge" as its brand (describing the product as IELTS
   preparation is fine; implying it is official is not).

2. **Web app first, PWA (plan Option A).** One React codebase that
   installs on phones like an app and caches the shell offline. No
   app-store listing at launch; a store wrapper (plan Option C) comes
   later only if usage justifies it.

3. **HashRouter, not BrowserRouter.** URLs look like
   `/#/dashboard`. Chosen because free static hosts (GitHub Pages,
   Render static) serve the app with no server rewrites, so deep links
   and refreshes never 404. Switch to BrowserRouter if the frontend
   ever moves to a host with rewrite rules.

4. **Auth: email + password only, JWT 7-day expiry.** Same pattern as
   FitTrack. Google sign-in was left out — add it only if learners
   ask for it.

5. **Database: SQLite locally, Postgres (Neon) in production.** The
   code already switches on `DATABASE_URL`. Neon is NOT provisioned
   yet — that needs your Neon account/decision at deploy time.

6. **Deploy: Render (static frontend + web-service backend).**
   `render.yaml` is in the repo. The backend will not run until
   1 Dec because Render's free web services are suspended until then
   (free hours exhausted). The frontend static site is unaffected.

7. **No practice content yet.** Module screens show the real format
   and a "Phase 2" notice. Phase 2 writes the original content:
   Listening recordings, Reading passages, Writing prompts, Speaking
   cue cards — in that order, per the plan.

8. **Vocabulary: add/list/delete only.** The spaced-repetition review
   schedule (interval growth on correct recall) is a Phase 2 study
   flow, not in this skeleton.

9. **Service worker caches the app shell only, never the API.**
   Auth and progress always go to the network, so a stale cache can
   never show another learner's data or an old score.

10. **Band estimates are always labelled.** Any band_estimate the API
    returns carries `band_label: "practice estimate, not an official
    score"`, and the UI repeats the label in the footer.

## Phase 2 (16 Nov 2026)

11. **Listening audio is pending real recordings.** No TTS tool exists
    in the sandbox (no espeak/festival; Google TTS via gTTS is
    rate-limited — 429 — from the shared egress IP, tried twice on two
    domains). Listening tests ship with full transcripts and a clear
    `audio_note`; the UI shows the transcript and says audio is coming.
    Samir records the 8 parts with a real voice (or volunteers do).
    Never ship fake or synthesised-placeholder audio files.
12. **Timed mode is enforced server-side.** A `TestSession` row is
    created on start; a timed submit past `started_at + limit + 60s
    grace` is refused with 400 and records no attempt. Practice mode
    has no limit. (Found during the build: SQLite returns naive
    datetimes, so the check coerces naive to UTC.)
13. **Band tables are the published approximations.** Listening,
    Academic Reading and GT Reading each have their own table (GT needs
    ~4–5 more correct answers per band); raw 0–2 maps to band 1.0
    (band 0 means "did not attempt"). Every band is labelled an
    estimate.
14. **Vocabulary items carry an `example` sentence.** The starter deck
    ships examples, so the model gained an `example` column (Phase 1
    dev databases predate it — delete `prepsathi.db` to recreate).
15. **Writing duration is the whole 60-minute session.** Both tasks
    are submitted with the session elapsed time; per-task splits are
    not tracked.
16. **Answers never leave the server before a submit.** Public test
    views strip answers, explanations and evidence; the review after
    submit is the only place they appear.
