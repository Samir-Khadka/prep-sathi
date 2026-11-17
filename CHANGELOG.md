# Phase 5 — second content batch (v0.5.0), 17 Nov 2026
- Second weekly content batch (all original): Listening L5–L8 (4 tests,
  160 questions, transcripts shown, audio still pending real recordings),
  Academic Reading RA5–RA6 and General Training Reading RG2 (3 tests,
  120 questions with evidence-linked explanations), 10 Writing prompts
  (WA-T1-06/07/08, WA-T2-06/07/08, WG-T1-06/07, WG-T2-06/07) with model
  answers + band-7 commentary — all 30 model answers still score 7.0–8.0
  under the Phase 3 feedback calibration, Speaking S16–S20, vocabulary
  deck 250 → 350 words (11 per topic, 12 general). Mock rotation extended
  to eight sittings per track (academic: L5+RA5, L6+RA6, L7+RA1, L8+RA2;
  general: L5+RG2, L6+RG1, L7+RG2, L8+RG1).
- Deferred: partner Speaking practice and the store wrapper (DECISIONS.md items 25–26).

# Phase 4 — launch readiness (v0.4.0), 16 Nov 2026
- Landing page: value proposition, how-it-works steps, free/no-paywall card, honest band labelling, and a privacy note page (recordings stay on-device, account/recording deletion). SEO basics: meta description, Open Graph tags, robots.txt, sitemap (root only — hash URLs are not crawlable; domain is a placeholder until a real deploy URL exists).
- In-app feedback loop: POST /api/feedback (authenticated) plus an admin list/resolve view gated by ADMIN_EMAILS (read from the environment at request time); feedback form page at /#/feedback.
- First weekly content batch (all original): Listening L4 (40 questions) and Academic Reading RA4 (40 questions), vocabulary deck 200 → 250 words. Mock rotation extended to a fourth sitting (L4+RA4, L4+RG1).
- LAUNCH.md: the exact 1 Dec flip-switch steps (Render blueprint, Neon DATABASE_URL, env vars, end-to-end checks, monitoring without 5-minute pings). Deploy assessment 16 Nov: no live deploy today — Render free web services still 503-suspended until 1 Dec; no accounts created, no signups attempted.
- Deferred: partner Speaking practice and the store wrapper (DECISIONS.md items 25–26).

# Phase 3 — full mocks and feedback (v0.3.0), 16 Nov 2026
- Full mock sittings in test order (Listening → Reading → Writing in
  one timed session, no breaks, no going back to a closed section;
  Speaking as a separate slot). Server-side section clocks (Listening
  1920s, Reading 3600s, Writing 3600s); an expired section is marked
  expired (score 0 / band 1.0) and the sitting continues. Overall band
  = average of the four section bands, IELTS rounding, always labelled
  "practice estimate, not an official score". Mock rotation gives each
  sitting fresh material (1st: L1+RA1, 2nd: L2+RA2, 3rd: L3+RA3, then
  wraps; GT uses RG1).
- Writing feedback by the four official criteria (task achievement,
  coherence and cohesion, lexical resource, grammatical range and
  accuracy) with per-criterion notes and an estimated band RANGE —
  guidance only, never an examiner's score. Calibrated so all 20 model
  answers score 7.0–8.0 and a weak fixture scores 4.0–5.0; limits are
  stated in every response (cannot judge ideas, argument quality, or
  factual accuracy).
- Speaking playback history: recordings saved on-device (IndexedDB,
  max 20), with playback, delete, and fluency signals (pace, pauses)
  giving an estimated range only. Nothing is uploaded, ever.
- Resources hub verified live (16 Nov): one link replaced — the
  British Council entry now points at the real familiarisation test
  instead of the generic UK preparation hub.
- New content (all original): Listening test L3 + Academic Reading
  test RA3 (3 Listening, 3 Academic + 1 GT Reading now).
- Backend 172 tests green; frontend typecheck + build green; full
  mock end-to-end smoke test passed (signup → mock → overall band).

# Phase 2 — MVP (v0.2.0), 16 Nov 2026
- Listening + Reading timed section tests with automatic scoring and
  estimated bands (published conversion tables, Academic and GT Reading
  use their own); practice mode with replay/review; server-enforced
  timings via test sessions (timed submit past limit + 60s grace is
  refused and records nothing).
- Content (all original): 2 Listening tests (8 transcripts, 80
  questions; audio pending — no TTS available in the sandbox), 2
  Academic + 1 General Training Reading tests (120 questions with
  evidence-linked explanations), 20 Writing prompts with model answers
  + band commentary, 15 Speaking sets, 200-word vocabulary starter deck.
- Vocabulary spaced-repetition review (interval doubles on correct
  recall to 60 days, resets on wrong) + starter-deck seed; dashboard
  with latest band per module, overall estimate, and recent attempts.
- Writing + Speaking are guided practice only (timers, word counts,
  on-device recording) — no automated feedback yet (Phase 3).
- Backend 147 tests green; frontend typecheck + build green; live
  smoke test passed against a real server.

# Phase 1 — skeleton (v0.1.0), 16 Nov 2026
- Repo, PWA shell, auth, database models, empty module screens,
  progress dashboard, official resources hub.
- No practice content yet (Phase 2).
