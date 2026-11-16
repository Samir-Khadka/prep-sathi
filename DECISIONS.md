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
