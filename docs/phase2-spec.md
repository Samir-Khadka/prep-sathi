# Phase 2 — MVP spec (the contract for this build)

Read this first. It is the single source of truth for Phase 2. The plan PDF
is at `~/workspace/your_files/ielts-prep-platform-plan/ielts-prep-platform-plan.pdf`.

## 0. Rules that apply to everyone

- All content is ORIGINAL, written fresh for this product. No copied test
  papers, passages, questions, answer keys, or audio; paraphrasing a copied
  passage is still copying. No Cambridge material anywhere.
- Every band estimate returned or shown carries
  `band_label: "practice estimate, not an official score"`, and the UI
  repeats the label wherever a band appears.
- Light premium design only: warm ivory `#FAF6ED`, royal violet `#5B3EA8`,
  antique gold. No black backgrounds. Keep HashRouter and the JWT auth.
- Timed mode enforces real timings server-side (see §3). Practice mode has
  no time limit.
- No real credentials in code, tests, or content. No literal
  credential-pattern strings anywhere.

## 1. Scoring tables (published conversion, raw /40 → band)

Tables are the widely published approximations (IDP/British Council/Cambridge
guidance); exact boundaries shift slightly between real test versions, which
is why every band is labelled an estimate. Band 0 is reserved for
"did not attempt", so raw 0–2 maps to band 1.0.

Listening (same for Academic and General Training):
39–40: 9.0, 37–38: 8.5, 35–36: 8.0, 32–34: 7.5, 30–31: 7.0, 26–29: 6.5,
23–25: 6.0, 18–22: 5.5, 16–17: 5.0, 13–15: 4.5, 10–12: 4.0, 8–9: 3.5,
6–7: 3.0, 4–5: 2.5, 3: 2.0, 0–2: 1.0

Academic Reading:
39–40: 9.0, 37–38: 8.5, 35–36: 8.0, 33–34: 7.5, 30–32: 7.0, 27–29: 6.5,
23–26: 6.0, 19–22: 5.5, 15–18: 5.0, 13–14: 4.5, 10–12: 4.0, 8–9: 3.5,
6–7: 3.0, 4–5: 2.5, 3: 2.0, 0–2: 1.0

General Training Reading:
40: 9.0, 39: 8.5, 37–38: 8.0, 36: 7.5, 34–35: 7.0, 32–33: 6.5, 30–31: 6.0,
27–29: 5.5, 23–26: 5.0, 19–22: 4.5, 15–18: 4.0, 12–14: 3.5, 9–11: 3.0,
6–8: 2.5, 4–5: 2.0, 3: 1.5, 0–2: 1.0

Overall band (when all four module bands exist): average of the four,
rounded to the nearest half band with .25 rounding UP to the next half and
.75 rounding UP to the next whole band (6.25 → 6.5, 6.75 → 7.0).
Implement as `floor(avg * 2 + 0.5) / 2`.

Short-answer matching: normalise both sides (lowercase, strip, collapse
whitespace, strip a trailing full stop) and compare against any accepted
alternative. MCQ: the submitted answer is the option index (0-based).
True/False/Not Given: answer is the string "TRUE", "FALSE" or "NOT GIVEN"
(case-insensitive).

## 2. Content JSON schemas (files under `backend/app/content/`)

All files are plain JSON, UTF-8, no trailing commas. Every question carries
an `explanation` and an `evidence` quote from the source text. Numbers are
unique 1–40 within a test, in order.

### 2a. `listening_tests.json` — 2 tests, 4 parts × 10 questions each

```json
{
  "tests": [
    {
      "id": "L1",
      "title": "Listening Test 1",
      "parts": [
        {
          "part": 1,
          "title": "Booking a library tour",
          "setting": "A new student phones the university library to ask about a tour.",
          "transcript": "NARRATOR: You will hear a student phoning a university library.\nSTUDENT: Good morning. I would like to book a place on the library tour...",
          "audio_url": null,
          "audio_note": "Audio is pending — Samir will record this with a real voice. Read the transcript once, as you would hear it once.",
          "questions": [
            {"no": 1, "type": "short", "prompt": "The library tour starts at ___", "answers": ["10.30", "10:30", "half past ten"], "explanation": "The librarian says the tour starts at half past ten.", "evidence": "LIBRARIAN: The morning tour starts at half past ten."},
            {"no": 2, "type": "mcq", "prompt": "What must students bring to the tour?", "options": ["A student card", "A passport", "A library form"], "answer": 0, "explanation": "...", "evidence": "..."}
          ]
        }
      ]
    }
  ]
}
```

- `type` is `"short"` (completion, answers = accepted alternatives, first is
  the canonical answer) or `"mcq"` (`answer` = 0-based option index).
- Transcript: dialogue with speaker labels, ~350–450 words per part,
  realistic IELTS progression (Part 1 everyday conversation, Part 2 everyday
  monologue, Part 3 educational discussion, Part 4 academic lecture).
- `audio_url` is ALWAYS null in Phase 2 (no TTS available in the sandbox;
  Google TTS is rate-limited from the shared IP). Do not invent audio files.

### 2b. `reading_tests.json` — 2 Academic + 1 General Training, 40 questions each

```json
{
  "tests": [
    {
      "id": "RA1", "track": "academic", "title": "Academic Reading Test 1",
      "passages": [
        {
          "section": 1, "title": "The Hidden Life of City Trees",
          "text": "Full passage text, several paragraphs, ~700-900 words...",
          "questions": [
            {"no": 1, "type": "tfng", "prompt": "City trees live longer than forest trees.", "answer": "FALSE", "explanation": "...", "evidence": "quote from the passage"},
            {"no": 5, "type": "mcq", "prompt": "What is the main purpose of the first paragraph?", "options": ["...", "...", "...", "..."], "answer": 1, "explanation": "...", "evidence": "..."},
            {"no": 9, "type": "short", "prompt": "Complete the sentence: Trees cool streets by releasing ___ into the air.", "answers": ["water vapour", "water vapor"], "explanation": "...", "evidence": "..."}
          ]
        }
      ]
    }
  ]
}
```

- `type` is `"tfng"` (answer "TRUE"/"FALSE"/"NOT GIVEN"), `"mcq"`
  (answer = 0-based index; matching-headings and matching-information are
  written as mcq with the headings/options listed), or `"short"`.
- Academic: 3 passages, ~13–14 questions each, 40 total. GT: 3 sections
  (Section 1: short everyday texts/notices, Section 2: workplace texts,
  Section 3: one longer general text), 40 total.
- Every answer has an `explanation` AND an `evidence` quote taken verbatim
  from the passage text.

### 2c. `writing_prompts.json` — 10 per track (20 total)

Academic: 5 × Task 1 + 5 × Task 2. General Training: 5 × Task 1 + 5 × Task 2.

```json
{
  "prompts": [
    {
      "id": "WA-T1-01", "track": "academic", "task": 1,
      "title": "Bus journeys in a small city",
      "prompt": "The table below shows the number of bus journeys made in Greenfield, a small city, in 2015 and 2025. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.\n\n[Data table: ...]",
      "min_words": 150, "suggested_minutes": 20,
      "model_answer": "Original model answer, ~190 words...",
      "commentary": "What makes this band 7: a clear overview, data grouped by pattern, range of comparison language, and only minor errors."
    }
  ]
}
```

- Task 1 Academic: describe a chart/graph/table/process — give the data in
  the prompt text (no images). GT Task 1: letters (formal/semi-formal/
  informal). Task 2: essays, both tracks.
- `model_answer` and `commentary` are original, written for this product.

### 2d. `speaking_sets.json` — 15 sets

```json
{
  "sets": [
    {
      "id": "S01", "topic": "A skill you would like to learn",
      "part1": ["What do you usually do in your free time?", "Do you enjoy learning new things?", "Did you learn any skills as a child?", "Is it better to learn alone or with a teacher?"],
      "part2": {"cue": "Describe a skill you would like to learn.", "points": ["what the skill is", "why you want to learn it", "how you would learn it", "how it would help you"], "prep_seconds": 60, "talk_seconds": 120},
      "part3": ["Do you think schools should teach practical skills?", "Is it ever too late to learn a new skill?", "How has technology changed the way people learn?", "Should employers pay for their workers to learn new skills?"],
      "sample_answer": "Short original sample talk for Part 2, ~180 words (optional but include where useful)."
    }
  ]
}
```

### 2e. `vocabulary_deck.json` — 200 words

```json
{
  "words": [
    {"word": "inevitable", "meaning": "certain to happen; unavoidable", "topic": "general", "example": "As the city grows, some traffic problems are inevitable."}
  ]
}
```

- Topics: education, health, environment, technology, work, society,
  science, culture, general. Academic word families and topic vocabulary.
- Every word has a meaning and an example sentence. No duplicates.

## 3. Backend API contract (new router `practice`)

Auth: all endpoints require the Phase 1 JWT except the content lists, which
are public. Base: `/api/practice`.

- `GET /api/practice/listening` → `[{id, title, parts: [{part, title, question_count, has_audio}], total_questions, time_limit_seconds}]`
  `time_limit_seconds` = 1920 (30 min + 2 min to check answers).
- `GET /api/practice/listening/{id}` → full test WITHOUT answers
  (questions carry prompt/options only; transcript included; `audio_url`
  null + `audio_note`).
- `POST /api/practice/listening/{id}/start` `{mode: "timed" | "practice"}`
  → `{session_id, started_at, time_limit_seconds | null, expires_at | null}`
- `POST /api/practice/listening/{id}/submit`
  `{session_id, answers: {"1": "10.30", "2": 0, ...}}`
  → `{score_raw, band_estimate, band_label, duration_seconds, overtime, results: [{no, correct, your_answer, correct_answer, explanation, evidence}]}`
  and records an Attempt (module=listening, kind="mock" if timed else
  "practice"). Timed submit after `expires_at` + 60s grace → 400
  "Time expired — your answers were not scored. Start again." No attempt
  is recorded for an expired submit. A session can be submitted once.
- Same four endpoints for reading: `/api/practice/reading`,
  `?track=academic|general` on the list, `time_limit_seconds` = 3600.
  Reading submit uses the track's own table (Academic vs GT).
- `GET /api/practice/writing?track=academic|general` → prompts WITHOUT
  model_answer/commentary: `[{id, track, task, title, prompt, min_words,
  suggested_minutes}]`.
- `GET /api/practice/writing/{id}` → full prompt WITH model_answer and
  commentary (client reveals these only after the learner submits).
- `POST /api/practice/writing/submit`
  `{prompt_id, text, duration_seconds}` →
  `{word_count, min_words, meets_minimum, attempt_id}` and records an
  Attempt (module=writing, kind=practice, band_estimate null — no
  automated feedback in Phase 2).
- `GET /api/practice/speaking` → `[{id, topic, part1, part2, part3,
  sample_answer}]`.
- `POST /api/practice/speaking/complete` `{set_id, duration_seconds}` →
  `{attempt_id}` and records an Attempt (module=speaking, kind=practice).
  Recording stays on the device (MediaRecorder); nothing is uploaded.
- `GET /api/vocabulary/due` → due VocabularyItems
  (`next_review <= now`, oldest first, max 50).
- `POST /api/vocabulary/{id}/review` `{correct: boolean}` → updated item.
  Correct: `interval_days = min(interval_days * 2, 60)` (1, 2, 4, 8, 16,
  32, 60); wrong: `interval_days = 1`. `next_review = now + interval`.
- `POST /api/vocabulary/seed` → adds the 200-word starter deck for the
  current user, skipping words already in their list.
  → `{added: number, skipped: number}`.
- `GET /api/dashboard` (extended): existing fields plus
  `latest_band_by_module: {module: band | null}`,
  `overall_estimate: number | null` (average of the four latest bands,
  IELTS rounding; null unless all four modules have a band),
  `attempts_recent: [{id, module, kind, score_raw, band_estimate,
  duration_seconds, created_at}]` (latest 10).

TestSession model: `id, user_id, module ("listening"|"reading"), test_id,
mode ("timed"|"practice"), started_at, time_limit_seconds (nullable),
submitted (bool)`.

## 4. Frontend routes & components (React + TS, HashRouter)

- `/practice/listening` — test list (mode picker per test: Timed / Practice).
- `/practice/listening/:id` — test runner: parts in order, questions,
  countdown timer in timed mode (auto-submits at 0), transcript block,
  audio element only if `audio_url` is set (it will not be in Phase 2 —
  show the `audio_note` instead), submit → results view: score, band +
  label, per-question correct/yours/correct-answer/explanation/evidence.
- `/practice/reading` and `/practice/reading/:id` — same runner shape,
  track filter on the list, passages shown with their questions, 60-min
  timer in timed mode.
- `/practice/writing` — track filter, prompt picker, one 60-minute session
  with a Task 1 prompt and a Task 2 prompt, live word counts against
  150/250, submit both → word counts + model answers revealed.
- `/practice/speaking` — set picker, Part 1 questions, Part 2 cue card +
  60s prep timer + 120s talk timer + record/playback/re-record via
  MediaRecorder, Part 3 questions, mark complete.
- `/vocabulary/review` — due cards one at a time, tap to reveal meaning +
  example, "I knew it" / "Not yet" → next card. Add a "Load starter deck"
  button on the Vocabulary page (calls seed).
- Dashboard — extend with: latest band per module, overall estimate vs
  target, recent attempts table (module, kind, raw, band, date).
- `src/api.ts` — add typed clients for every new endpoint above.
- ModulePage: replace the "Coming in Phase 2" notice with links to the
  new practice routes once content exists.

## 5. Tests (backend, `backend/tests/`)

- `test_scoring.py` — every boundary of all three tables (including 0, 2,
  3, 39, 40), overall-band rounding (6.25 → 6.5, 6.75 → 7.0),
  short-answer normalisation.
- `test_content.py` — loads every content file: counts (2 listening × 40,
  2 academic × 40, 1 GT × 40, 20 writing prompts, 15 speaking sets,
  200 vocab words), unique question numbers 1–40, MCQ indices in range,
  tfng values valid, no empty strings, every question has explanation +
  evidence.
- `test_practice.py` — list/get endpoints, start→submit happy path for
  listening and reading (timed + practice), scoring correctness end to
  end, expired timed submit → 400 with no attempt recorded, double
  submit → 400, wrong-user session → 403/404, writing submit word
  counts, speaking complete, vocab review interval growth + reset,
  vocab seed idempotency, dashboard extension fields.
