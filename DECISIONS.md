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

## Phase 3 (16 Nov 2026)

17. **A mock is one sitting, in test order, with no going back.**
    Listening → Reading → Writing run back-to-back with server-side
    clocks; submitting a closed section returns 400. An expired
    section is marked expired (score 0 / band 1.0) and the sitting
    continues — a missed section never blocks the rest of the mock.
18. **Overall band needs all four sections.** Writing contributes the
    midpoint of its feedback range; Speaking contributes the midpoint
    of the on-device fluency range (if the learner completes Speaking
    without a range, the overall stays null until a ranged completion
    is recorded). If Writing expires, the sitting can never complete
    with an overall band — stated in the code and covered by a test.
19. **Writing feedback is heuristic and says so.** It counts
    measurable patterns (word count, paragraph structure, linking
    words, lexical variety, sentence variety) and cannot judge ideas,
    argument quality, or factual accuracy. Every response carries a
    `limits` field and the practice-estimate label. No article /
    spelling / punctuation detection is attempted.
20. **Speaking recordings never leave the device.** History lives in
    IndexedDB (max 20 recordings, oldest dropped), playback and
    delete are local, and no audio is sent in any API call. Fluency
    signals are timing only (speech seconds, pause count, longest
    pause) and give a band RANGE, never a precise score.
21. **Mock rotation is per user, per track.** 1st mock: L1+RA1 (or
    L1+RG1 for GT), 2nd: L2+RA2, 3rd: L3+RA3, then wraps; Writing
    prompts rotate in definition order. A learner's second mock uses
    fresh material.
22. **Resources hub links are verified live.** 16 Nov 2026: four of
    five links confirmed; the British Council familiarisation entry
    was repointed from the generic UK preparation hub to the actual
    familiarisation test page.
23. **Mock speaking reuses the speaking-history fluency module.**
    The mock runner mirrors the PracticeSpeaking recording flow
    rather than embedding that page (it is a full page with its own
    practice completion call). Fluency ranges flow from the saved
    recording into the mock's speaking completion.
24. **Feedback is imported lazily in the mock router.** The mock
    writing endpoint imports `analyse_writing` inside the handler
    (503 if absent) so the app stays bootable if the feedback module
    is ever missing; in the shipped tree it is always present.

## Phase 4 (16 Nov 2026)

25. **Partner Speaking practice is DEFERRED.** Needs real learner
    demand first — no pairing system until learners ask for it.
26. **Store wrapper (PWA → app stores) is DEFERRED.** Needs real web
    usage first — no app-store listing until the web app is actually
    being used.
