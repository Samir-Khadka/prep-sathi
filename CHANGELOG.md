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
