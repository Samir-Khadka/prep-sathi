# Phase 3 — Automated Writing feedback: signals, limits, calibration

Backend only. Implementation: `backend/app/feedback.py`
(`analyse_writing(prompt, text)`), endpoint
`POST /api/practice/writing/feedback`, tests
`backend/tests/test_feedback.py`. The mock engine imports
`analyse_writing` directly, so its signature and response shape are a
contract — do not change them without coordinating with the mock engine.

## What it is

Guidance only, never an examiner's score. Every response carries
`band_label: "practice estimate, not an official score"` and a `limits`
field (wording in `feedback.py`, constant `LIMITS`). The band is a
*range* (centre ± 0.5, clamped to 4.0–8.0, in 0.5 steps); the overall
range is the average of the four criterion ranges, rounded to 0.5.

## Limits (also stated in every response)

Automated feedback counts measurable patterns in the text (length,
linking words, vocabulary variety, sentence variety). It **cannot**
judge ideas, argument quality, or factual accuracy the way a human
examiner can, and it never promises a band or an outcome in a real
test.

It also does **not** claim to detect errors it cannot detect:

- No article ("a" vs "an"), spelling, punctuation, or subject–verb
  agreement checking — those need a real grammar checker or a human.
- No judgement of whether an answer is really on topic beyond
  counting prompt key words; a text can repeat the prompt's words
  without answering it.
- "Sentences without a verb" is a heuristic (auxiliary / irregular
  verb / verb-stem match), not a parse — it can miss real verbs and
  can be fooled by unusual vocabulary. Notes say "may be missing".

## Signals (all directly countable; every note cites its measurement)

Word count counts **alphabetic tokens** (`[a-z]+`, apostrophes kept):
"income-based" is two tokens, "420,000" is none. This differs from the
submit endpoint, which counts whitespace-split words — the feedback
count is the one used for all analysis.

### Task achievement (10 points)

| Signal | Points | Thresholds |
|---|---|---|
| Length vs minimum | 4 | ratio ≥1.0 → 4; ≥0.9 → 3.5; ≥0.8 → 3; ≥0.6 → 2; ≥0.4 → 1; else 0 |
| Prompt key-word coverage (distinct content words of the prompt present in the text; instruction words excluded) | 3 | ≥0.5 → 3; ≥0.35 → 2; ≥0.2 → 1; else 0 |
| Structure signal | 3 | present → 3, else 0. Academic Task 1: an overview phrase ("overall", "it is clear", "the chart shows", …) in the first 3 sentences. General Task 1: a greeting ("dear", "hi", "hello") or "I am writing…" in the first 3 sentences. Task 2: a position phrase ("in my opinion", "I believe", "I think", "in conclusion", …) anywhere. |

Under-length **caps** the score: ratio < 0.5 → max 3.0 (band ≤ 5.0);
0.5–0.8 → max 4.0 (band ≤ 5.5); 0.8–1.0 → max 5.0 (band ≤ 6.0).

### Coherence and cohesion (7 points, scaled to 10)

| Signal | Points |
|---|---|
| Paragraphs | 3: ≥3 paragraphs → 3; 2 → 2.5; 1 paragraph ≥200 words → 2.5; 150–199 → 1; <150 → 0 |
| Distinct linking words (fixed list of ~40: however, furthermore, in contrast, as a result, for example, firstly, in conclusion, then, next, first, …) | 3: Task 1 ≥3 distinct → 3, 2 → 2, 1 → 1, 0 → 0; Task 2 ≥5 → 3, 3–4 → 2, 1–2 → 1, 0 → 0 |
| Opening picks up ≥2 prompt key words | 1 |
| Penalties (−0.5 each) | one-sentence paragraph (with ≥2 paragraphs); one paragraph holding >75% of words; most-used linker ≥4 times |

Why the single-paragraph credit: the product's own model answers are
stored as one long block (no blank lines), so a long single paragraph
earns partial credit — the missing breaks are still flagged in the
notes. Task 1 uses a lower linker bar than Task 2 because short
descriptive texts and letters legitimately use fewer linking words
than a 250-word essay.

### Lexical resource (10 points)

| Signal | Points | Thresholds |
|---|---|---|
| Type-token ratio (distinct words / all words) | 3 | ≥0.55 → 3; ≥0.50 → 2.5; ≥0.45 → 2; ≥0.40 → 1.5; else 0.5 |
| Academic words (fixed list of ~95 formal words, including formal letter words such as grateful, concerned, regarding; linking adverbs excluded — they count under coherence) | 3 | ≥4 distinct → 3; 2–3 → 2; 1 → 1; 0 → 0 |
| Top-word repetition (most frequent non-stopword, excluding prompt key words plural-aware — repeating topic words is expected) | 2 | ≤7 → 2; 8–10 → 1; ≥11 → 0 |
| Collocation variety: repeated content-word bigrams | 2 | share of distinct bigrams (built inside sentences, ignoring pairs made only of prompt words) that occur ≥2 times: ≤0.03 → 2; ≤0.06 → 1.5; ≤0.10 → 1; >0.10 → 0 |

Distinct bigrams are *not* scored on their own: in practice almost
every adjacent pair is new, so the count mostly measures text length.
What discriminates is how often pairs repeat.

### Grammatical range and accuracy (10 points)

| Signal | Points | Thresholds |
|---|---|---|
| Sentence-length variety (population stdev of words per sentence) | 3 | ≥6 → 3; ≥4 → 2.5; ≥2.5 → 2; ≥1.5 → 1; else 0.5 |
| Complex sentences: distinct subordinators/relatives (although, because, while, which, who, if, when, since, … — "that" and "as" excluded as too common to discriminate) + participial -ing clauses ("attracting 420,000 visitors"; common -ing nouns such as morning, wedding excluded) | 3 | ≥4 distinct → 3; 3 → 2; 2 → 1.5; 1 with ≥2 participial sentences → 1; 1 → 0.5; 0 with ≥2 participial → 1; else 0 |
| Detectable errors (−1 each, floor 0, from 4) | 4 | a sentence over 45 words; a sentence (≥4 words) with no detectable verb; "very" ≥3 times; ≥3 sentences opening with "I think" |

## Score → band mapping

Score out of 10 → centre band: ≥9.0 → 8.0; ≥8.0 → 7.5; ≥7.0 → 7.0;
≥6.0 → 6.5; ≥5.0 → 6.0; ≥4.0 → 5.5; ≥3.0 → 5.0; ≥2.0 → 4.5;
else 4.0. Criterion range = centre ± 0.5 (clamped 4.0–8.0). Overall
low/high = average of criterion lows/highs, rounded to 0.5.

## Calibration (2026-11-16, from the product's own content)

Thresholds were set from the 30 model answers in
`backend/app/content/writing_prompts.json` and one weak fixture
(original text, in `backend/tests/test_feedback.py` as `WEAK_TEXT`:
115 words, one paragraph, repetitive vocabulary, near-identical
sentence lengths, "very" ×5, six "I think" openers).

| Text | Overall band range |
|---|---|
| All 30 model answers (Task 1 academic + general, Task 2 academic + general) | low end 7.0–7.5, high end 7.5–8.0 (weakest: WA-T1-06, WA-T1-07, WA-T1-08 at 7.0–8.0 — Task 1 descriptions score lower on coherence, which is expected: single-paragraph storage, few linking words, plain vocabulary) |
| Weak fixture (WA-T2-01 prompt) | 4.0–5.0 (TA 4.5–5.5, CC 4.0–5.0, LEX 4.0–5.0, GRAM 4.5–5.5) |

Pinned in tests: `test_model_answers_score_high` (every model answer
≥ 7.0 low end) and `test_weak_fixture_scores_low` (weak fixture
≤ 5.5 high end). If content or thresholds change and these fail, the
thresholds need re-tuning from the samples, not from vibes — see the
calibration notes above for which signals move which criterion.

## Endpoint

`POST /api/practice/writing/feedback` — auth required (401 without a
token), unknown `prompt_id` → 404, empty/whitespace-only `text` → 400.
Returns exactly the `analyse_writing` dict (the endpoint test asserts
equality). No attempt is recorded; saving a practice attempt is still
`POST /api/practice/writing/submit`, whose behaviour is unchanged.
Request/response models live in `feedback.py` itself (not `schemas.py`).
