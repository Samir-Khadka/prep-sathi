# Listening recording guide (Phase 5.2)

PrepSathi's Listening tests are written and ready — every part has a
full transcript — but none of them has audio yet. The recordings are
the one piece that cannot be faked: they must be a **real human voice**
— yours, or a volunteer's — reading the transcript. Never synthesised
speech, never text-to-speech, never a placeholder tone or silence file.
A synthesised voice would mislead learners who are training their ear
for a real exam, and it is not what this app promises.

## What to record

**32 files** — 8 tests × 4 parts:

| Test | Parts |
| ---- | ----- |
| L1–L8 | Part 1, Part 2, Part 3, Part 4 each |

One file per part. The transcript for each part is shown in the app
under "Read the transcript" on that part's page, and it is also in
`backend/app/content/listening_tests.json` under that test and part.

## File specs

- **Format:** MP3 (`.mp3`), mono, **~64 kbps** — small enough to
  download on a phone, clear enough for speech.
- **Naming:** the file name must match the path the app serves:
  `backend/app/static/audio/listening/<TEST_ID>/part<N>.mp3`,
  e.g. `L5/part1.mp3`. A wrong name means the part stays silent.
- **Voice:** one speaker per part, as the transcript stages it
  (narrator + the speakers in the dialogue — read all voices yourself,
  or record with a partner and keep each speaker consistent within a
  part). Speak clearly, at a natural exam pace — not rushed, not
  slowed down.
- **Room:** a quiet room, phone on a stable surface, no background
  music, TV, traffic, or fan noise. Record a 5-second test first and
  listen back on earphones before doing a whole part.
- **Script:** read the transcript **exactly** — every word, including
  the numbers, names, and spellings in it. Do not paraphrase, skip, or
  add words: learners answer questions from what they hear, and the
  answer key is written against the transcript.

## How to hand the files over

Pick whichever is easier — both end in the same place:

1. **Admin upload (no code changes).** In the app, as an admin, send
   each file to `POST /api/audio/listening/<TEST_ID>/part<N>` as a
   multipart `file` field (MP3, max 20 MB). The upload writes the file
   to `backend/app/static/audio/listening/` **and** sets that part's
   `audio_url` in `listening_tests.json` in the same step, so the part
   plays immediately — no restart, no deploy.
2. **Commit the files + the JSON change.** Put the 32 MP3s under
   `backend/app/static/audio/listening/<TEST_ID>/part<N>.mp3` and set
   each part's `audio_url` to the matching
   `/static/audio/listening/<TEST_ID>/part<N>.mp3` path in
   `backend/app/content/listening_tests.json`. The content validator
   rejects any `audio_url` that does not name its own test and part,
   so a typo fails loudly instead of playing the wrong recording.

## Checklist before a file counts as done

- [ ] File name and folder match the table above exactly.
- [ ] MP3, mono, ~64 kbps.
- [ ] Read the transcript word-for-word, one consistent speaker per part.
- [ ] Listened back on earphones: clear, no clipping, no background noise.
- [ ] After upload/commit, the part shows a player in the app (not the
      "audio pending" note) and plays from start to finish.

## What the player does with your recording

- Learners get play/pause, a seek slider with current/total time, and
  "Now playing: Part N". Starting one part pauses any other part.
- A downloaded recording is cached on the learner's device
  (`prepsathi-audio-v1`) so it keeps playing offline; the service
  worker never caches audio itself.
- If a recording ever fails to load, the app falls back to the audio
  note + transcript — it never shows a broken player.
