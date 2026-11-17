# Phase 3 — full mocks and feedback (v0.3.0), the contract for this build

Read this first. It is the single source of truth for Phase 3. The plan PDF
is at `~/workspace/your_files/ielts-prep-platform-plan/ielts-prep-platform-plan.pdf`.
Phase 2's contract lives in `docs/phase2-spec.md`; nothing there changed
except the content counts below.

## 0. Rules that apply to everyone

- All content is ORIGINAL, written fresh for this product. No copied test
  papers, passages, questions, answer keys, or audio; paraphrasing a copied
  passage is still copying. No Cambridge material anywhere.
- Every band estimate returned or shown carries
  `band_label: "practice estimate, not an official score"`, and the UI
  repeats the label wherever a band appears. Writing and Speaking give
  estimated RANGES, never a precise band, and never promise a band or
  an outcome.
- Light premium design only: warm ivory `#FAF6ED`, royal violet `#5B3EA8`,
  antique gold. No black backgrounds. Keep HashRouter and the JWT auth.
- Timed mode enforces real timings server-side. No real credentials in
  code, tests, or content. No literal credential-pattern strings.

## 1. Full mock sittings (`/api/mock`, `backend/app/routers/mock.py`)

A mock runs in test order — Listening → Reading → Writing in one sitting,
no breaks, no going back to a closed section; Speaking is a separate slot.

- `POST /api/mock/start {"track": "academic"|"general"}` → 201, starts
  the Listening clock (1920s). The server rotates test combinations per
  user: 1st mock L1+RA1, 2nd L2+RA2, 3rd L3+RA3, then wraps; GT uses
  RG1 for Reading. Writing prompts are the first unused of the
  track/task in definition order, wrapping once all 5 are used.
- `GET /api/mock` → the user's mock sessions, newest first.
  `GET /api/mock/{mock_id}` → full status incl. per-section results.
- `POST /api/mock/{mock_id}/listening/submit` and `.../reading/submit`
  take a Phase 2 `TestSession` (started via `/api/practice/.../start`)
  and score with the Phase 2 tables. Submitting a closed section → 400
  ("That section is closed — a mock runs in test order and you cannot
  go back"). An expired section is marked `"expired"` (score 0, band
  1.0, no Attempt recorded) and the sitting advances — a missed section
  never blocks the rest of the mock.
- `POST /api/mock/{mock_id}/writing/submit {"task1_text", "task2_text",
  "duration_seconds"}` → per-task word counts + `analyse_writing`
  feedback (see §2). Writing clock is 3600s for both tasks together.
  An expired writing submit → 400, section marked expired, sitting
  advances to Speaking; an expired mock can never complete with an
  overall band.
- `POST /api/mock/{mock_id}/speaking/complete {"set_id",
  "duration_seconds", "band_low", "band_high"}` → stores the speaking
  band as the midpoint of the provided fluency range. Without a range
  the section stays active (completable later); a one-sided range →
  400. When all four section bands exist, `overall_band` =
  `overall_band([listening, reading, writing_midpoint, speaking])`
  (IELTS rounding, §1 of phase2-spec.md) and status becomes
  `"complete"`.
- Every endpoint requires JWT; another user's mock → 403; unknown mock
  → 404. Five mock Attempts are recorded per completed sitting
  (Listening, Reading, 2× Writing, Speaking).

## 2. Writing feedback (`backend/app/feedback.py`)

`analyse_writing(prompt, text)` returns per-criterion band ranges plus
an overall range (average of the four criteria, rounded to .5):

```
{"prompt_id", "word_count", "min_words", "meets_minimum",
 "band_low", "band_high", "band_label",
 "criteria": {"task_achievement": {"band_low", "band_high", "notes": [...]},
              "coherence": {...}, "lexical": {...}, "grammar": {...}},
 "limits": "..."}
```

- Signals are measurable patterns only: word count vs minimum, prompt
  key-word coverage, paragraph structure and balance, distinct linking
  devices, type-token ratio, academic-word hits, repeated-word overuse,
  sentence-length variety, subordinating-conjunction signals. See
  `docs/phase3-feedback-notes.md` for the full signal list, thresholds
  and calibration.
- Calibration: all 30 model answers score 7.0–8.0; a weak fixture
  (115 words, single paragraph, repetitive) scores 4.0–5.0.
- Limits (stated in every response): automated feedback counts
  measurable patterns only and **cannot judge ideas, argument quality,
  or factual accuracy the way a human examiner can, and never promises
  a band or an outcome**. No article/spelling/punctuation/agreement
  detection is attempted.
- Endpoint: `POST /api/practice/writing/feedback` (auth required,
  unknown prompt → 404, empty text → 400). The existing writing submit
  is unchanged.

## 3. Speaking playback history (`frontend/src/speakingHistory.ts`)

- Recordings live in IndexedDB on the device (max 20, oldest dropped),
  with metadata (set, topic, part, date, duration, fluency) and blobs
  loaded on demand. Playback, per-recording delete, delete-all. Nothing
  is uploaded, ever; no audio appears in any API call.
- Fluency signals are timing only: an AnalyserNode samples mic RMS
  ~10×/s during recording; pauses are silence gaps > 0.7s. Reported:
  speech seconds, pause count, longest pause, and an estimated band
  range (≥80% of the 120s target with few pauses → 6.5–7.5; frequent
  long pauses or stopping far short → 4.5–5.5). The range is guidance
  from timing signals only — it cannot judge pronunciation, vocabulary,
  or ideas.
- Saving is explicit ("Save this recording to my history"), never
  automatic. The history lives on the Speaking practice page; the mock
  runner reads a saved recording's fluency range for its Speaking step.

## 4. Frontend mock UI (`/mock`, `/mock/:id`, `/mock/:id/results`)

- Mock list: explains the sitting, track picker, start button, past
  mocks with status + overall band.
- Runner: renders the current section only, with a progress strip and a
  countdown from the server's `section_expires_at`; auto-submit at 0.
  Listening/Reading reuse the Phase 2 runners; Writing is Task 1 +
  Task 2 in one 60-minute session with live word counts; Speaking
  reuses the on-device recording flow. No back button to a closed
  section. The mock detail endpoint does not carry test/prompt IDs, so
  the runner remembers them from the start response in localStorage
  (see `frontend/src/pages/mockPlan.ts`).
- Results: per-section bands, writing band range with per-criterion
  notes, speaking band if present, overall band when all four exist.
  Every band labelled a practice estimate.

## 5. Resources hub (verified live 16 Nov 2026)

| URL | Status |
|---|---|
| https://ielts.org | 200 |
| https://takeielts.britishcouncil.org/take-ielts/prepare/ielts-ready | live (curl blocked by bot protection; page fetched) |
| https://takeielts.britishcouncil.org/prepare/ielts-free-practice-mock-tests/ielts-familiarisation-test | live — replaced the old UK preparation-hub URL, which was the wrong page for the description |
| https://ielts.idp.com/about/ielts-familiarisation-tests | 200 |
| https://ielts.idp.com/srilanka/results/scores | 200 |

## 6. Content counts after Phase 3

Listening: 3 tests (L1, L2, L3), 120 questions. Reading: 3 Academic
(RA1–RA3) + 1 General Training (RG1), 160 questions. Writing: 20
prompts. Speaking: 15 sets. Vocabulary: 200 words. All original.

## 7. Tests

- `backend/tests/test_mock.py` (14 tests): rotation, full happy path
  with overall-band math, section lock, expired listening/writing,
  wrong-user 403, unknown-mock 404, writing feedback shape,
  speaking-without-range.
- `backend/tests/test_feedback.py` (11 tests): shape, calibration
  (model answers ≥ 7.0 low end, weak fixture ≤ 5.5 high end), word
  counts, 404/401, endpoint parity with `analyse_writing`.
- Frontend: `tsc` + `vite build` green; fluency math checked 23/23
  (esbuild-compiled, one-off script in /tmp); IndexedDB history
  exercised in headless Chromium (save/list/blob round-trip/20-cap/
  delete/clear).
- Full backend suite: 172 passed. Coordinator integration smoke test:
  signup → mock start → L/R/W submits → speaking complete → overall
  band 4.0 (empty L/R answers, model-answer writing, 6.0–7.0
  speaking) with status complete; closed-section re-submit → 400.
