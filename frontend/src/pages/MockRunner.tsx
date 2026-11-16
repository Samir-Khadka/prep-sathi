/* Full-mock runner: renders the mock's CURRENT section only.
   Listening → Reading → Writing → Speaking, in test order, with no
   way back to a closed section. Each section has its own countdown
   from the server's section_expires_at and auto-submits at 0.
   Listening/Reading reuse the practice runners' question inputs and
   results view; Writing reuses the 60-minute two-task shape;
   Speaking reuses the on-device recording + fluency flow. */

import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  api,
  BAND_LABEL,
  type ListeningTest,
  type MockDetail,
  type MockStartResponse,
  type MockSubmitResult,
  type MockTrack,
  type MockWritingSubmitResult,
  type ReadingTest,
  type SpeakingSet,
  type SubmitResult,
  type TestSession,
  type WritingPromptSummary,
} from "../api";
import { useAuth } from "../auth";
import {
  BandLabel,
  formatTime,
  QuestionInput,
  ResultsView,
  useCountdown,
  type AnswerValue,
} from "./practiceShared";
import {
  deriveMockPlan,
  loadMockPlan,
  saveMockPlan,
  saveMockResults,
  type MockPlan,
} from "./mockPlan";
import {
  createFluencyTracker,
  saveSpeakingRecording,
  type FluencyEstimate,
  type FluencyTracker,
} from "../speakingHistory";

const SECTION_ORDER = ["listening", "reading", "writing", "speaking"] as const;
const SECTION_LABELS: Record<string, string> = {
  listening: "Listening",
  reading: "Reading",
  writing: "Writing",
  speaking: "Speaking",
};

function wordCount(text: string): number {
  const trimmed = text.trim();
  return trimmed === "" ? 0 : trimmed.split(/\s+/).filter(Boolean).length;
}

/** Seconds left on the server's section clock, computed once per section. */
function useSectionClock(
  expiresAt: string | null,
  key: string,
): number | null {
  const [start, setStart] = useState<number | null>(null);
  useEffect(() => {
    if (!expiresAt) {
      setStart(null);
      return;
    }
    setStart(
      Math.max(0, Math.round((Date.parse(expiresAt) - Date.now()) / 1000)),
    );
  }, [expiresAt, key]);
  return start;
}

function ProgressStrip({
  mock,
}: {
  mock: MockDetail;
}) {
  return (
    <ol className="mock-steps">
      {SECTION_ORDER.map((key) => {
        const status = mock.sections[key].status;
        const isCurrent = mock.current_section === key;
        const cls =
          status === "done"
            ? "mock-step done"
            : status === "expired"
              ? "mock-step expired"
              : isCurrent
                ? "mock-step active"
                : "mock-step";
        return (
          <li key={key} className={cls}>
            {status === "done" ? "✓ " : ""}
            {SECTION_LABELS[key]}
            {status === "expired" ? " (expired)" : ""}
            {isCurrent && status !== "done" ? " — now" : ""}
          </li>
        );
      })}
    </ol>
  );
}

/* ------------------------------------------------------------------ */
/* Listening / Reading sections (shared shape)                         */
/* ------------------------------------------------------------------ */

function ScoredSection({
  mockId,
  kind,
  testId,
  expiresAt,
  onAdvance,
}: {
  mockId: number;
  kind: "listening" | "reading";
  testId: string;
  expiresAt: string | null;
  onAdvance: () => void;
}) {
  const [test, setTest] = useState<ListeningTest | ReadingTest | null>(null);
  const [session, setSession] = useState<TestSession | null>(null);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [result, setResult] = useState<MockSubmitResult | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittedRef = useRef(false);

  const clockKey = `${mockId}:${kind}`;
  const clockStart = useSectionClock(expiresAt, clockKey);

  useEffect(() => {
    if (kind === "listening") {
      api
        .listeningTest(testId)
        .then(setTest)
        .catch(() => setError("Could not load this test."));
      api
        .startListening(testId, "timed")
        .then(setSession)
        .catch((err: unknown) =>
          setError(
            err instanceof Error ? err.message : "Could not start the test.",
          ),
        );
    } else {
      api
        .readingTest(testId)
        .then(setTest)
        .catch(() => setError("Could not load this test."));
      api
        .startReading(testId, "timed")
        .then(setSession)
        .catch((err: unknown) =>
          setError(
            err instanceof Error ? err.message : "Could not start the test.",
          ),
        );
    }
  }, [kind, testId]);

  const submit = useCallback(async () => {
    if (!session || submittedRef.current || submitting) return;
    submittedRef.current = true;
    setSubmitting(true);
    const payload: Record<string, string | number> = {};
    for (const [k, v] of Object.entries(answers)) {
      if (v !== undefined && v !== "") payload[k] = v;
    }
    try {
      const res =
        kind === "listening"
          ? await api.submitMockListening(mockId, session.session_id, payload)
          : await api.submitMockReading(mockId, session.session_id, payload);
      setResult(res);
      saveMockResults(mockId, {
        [kind]: {
          score_raw: res.score_raw,
          band_estimate: res.band_estimate,
          duration_seconds: res.duration_seconds,
          results: res.results,
        },
      });
    } catch (err) {
      submittedRef.current = false;
      setError(
        err instanceof Error ? err.message : "Could not submit your answers.",
      );
    } finally {
      setSubmitting(false);
    }
  }, [kind, mockId, session, answers, submitting]);

  const submitRef = useRef(submit);
  submitRef.current = submit;

  const remaining = useCountdown(
    clockStart,
    clockStart !== null && !!session && !result,
    useCallback(() => {
      void submitRef.current();
    }, []),
  );

  if (error && !test) return <p className="error">{error}</p>;
  if (!test || !session) return <p>Loading…</p>;
  if (result) {
    const nextLabel =
      result.next_section === "reading"
        ? "Continue to Reading"
        : "Continue to Writing";
    const plain: SubmitResult = result;
    return (
      <>
        <ResultsView result={plain} title={test.title} />
        {result.overtime && (
          <p className="notice">
            This section ran out of time, so it was marked expired and the
            mock moved on.
          </p>
        )}
        <p>
          <button onClick={onAdvance}>{nextLabel}</button>
        </p>
      </>
    );
  }

  function setAnswer(no: number, value: string | number) {
    setAnswers((prev) => ({ ...prev, [String(no)]: value }));
  }

  const isListening = kind === "listening";
  const listening = isListening ? (test as ListeningTest) : null;
  const reading = !isListening ? (test as ReadingTest) : null;

  return (
    <>
      <section className="hero">
        <h1>
          {test.title} — {SECTION_LABELS[kind]}
        </h1>
        <p className="lead">
          {isListening
            ? "Timed mock — the section auto-submits when the timer ends. Read each transcript once, as you would hear it once."
            : "Timed mock — the section auto-submits when the timer ends."}{" "}
          You cannot go back to this section once it is submitted.
        </p>
        {remaining !== null && (
          <p className="timer">
            Time left: <strong>{formatTime(remaining)}</strong>
          </p>
        )}
      </section>

      {error && <p className="error">{error}</p>}

      {listening &&
        listening.parts.map((part) => (
          <section key={part.part} className="card">
            <h2>
              Part {part.part}: {part.title}
            </h2>
            <p className="meta">{part.setting}</p>
            {part.audio_url ? (
              <audio controls src={part.audio_url}>
                Your browser does not support audio playback.
              </audio>
            ) : (
              <p className="notice">{part.audio_note}</p>
            )}
            <details className="transcript">
              <summary>Read the transcript</summary>
              <p style={{ whiteSpace: "pre-wrap" }}>{part.transcript}</p>
            </details>
            <ol className="questions">
              {part.questions.map((q) => (
                <li key={q.no} className="question">
                  <p>
                    <strong>Q{q.no}.</strong> {q.prompt}
                  </p>
                  <QuestionInput
                    question={q}
                    value={answers[String(q.no)]}
                    onChange={(v) => setAnswer(q.no, v)}
                    disabled={submitting}
                  />
                </li>
              ))}
            </ol>
          </section>
        ))}

      {reading &&
        reading.passages.map((passage) => (
          <section key={passage.section} className="card">
            <h2>
              Section {passage.section}: {passage.title}
            </h2>
            <div className="passage" style={{ whiteSpace: "pre-wrap" }}>
              {passage.text}
            </div>
            <ol className="questions">
              {passage.questions.map((q) => (
                <li key={q.no} className="question">
                  <p>
                    <strong>Q{q.no}.</strong> {q.prompt}
                  </p>
                  <QuestionInput
                    question={q}
                    value={answers[String(q.no)]}
                    onChange={(v) => setAnswer(q.no, v)}
                    disabled={submitting}
                  />
                </li>
              ))}
            </ol>
          </section>
        ))}

      <p>
        <button onClick={() => void submit()} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit this section"}
        </button>
      </p>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Writing section: Task 1 + Task 2 in one 60-minute session.          */
/* ------------------------------------------------------------------ */

const CRITERION_LABELS: Record<string, string> = {
  task_achievement: "Task achievement",
  coherence: "Coherence and cohesion",
  lexical: "Lexical resource",
  grammar: "Grammatical range and accuracy",
};

function WritingSection({
  mockId,
  track,
  plan,
  expiresAt,
  onAdvance,
}: {
  mockId: number;
  track: MockTrack;
  plan: MockPlan;
  expiresAt: string | null;
  onAdvance: () => void;
}) {
  const [prompts, setPrompts] = useState<WritingPromptSummary[]>([]);
  const [task1Text, setTask1Text] = useState("");
  const [task2Text, setTask2Text] = useState("");
  const [result, setResult] = useState<MockWritingSubmitResult | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittedRef = useRef(false);

  const clockKey = `${mockId}:writing`;
  const clockStart = useSectionClock(expiresAt, clockKey);

  useEffect(() => {
    api
      .writingPrompts(track)
      .then(setPrompts)
      .catch(() => setError("Could not load the writing prompts."));
  }, [track]);

  const task1 = prompts.find((p) => p.id === plan.writing_task1_prompt_id);
  const task2 = prompts.find((p) => p.id === plan.writing_task2_prompt_id);

  // Remaining seconds, kept in a ref so the auto-submit always uses the
  // latest value without re-creating the submit callback.
  const remainingRef = useRef<number | null>(null);

  const submit = useCallback(
    async (auto: boolean) => {
      if (!task1 || !task2 || submittedRef.current || submitting) return;
      if (!auto && (task1Text.trim() === "" || task2Text.trim() === "")) {
        setError(
          "Write at least a few words for both tasks before submitting.",
        );
        return;
      }
      submittedRef.current = true;
      setSubmitting(true);
      setError("");
      // The server requires at least one character per task. On an
      // auto-submit at 0 an untouched task is sent as a single space,
      // so the section still closes honestly at the floor band.
      const t1 = task1Text.trim() === "" ? " " : task1Text;
      const t2 = task2Text.trim() === "" ? " " : task2Text;
      const duration =
        clockStart !== null && remainingRef.current !== null
          ? Math.max(0, clockStart - remainingRef.current)
          : 0;
      try {
        const res = await api.submitMockWriting(mockId, t1, t2, duration);
        setResult(res);
        saveMockResults(mockId, {
          writing: {
            task1: {
              word_count: res.task1.word_count,
              min_words: res.task1.min_words,
              meets_minimum: res.task1.meets_minimum,
              feedback: {
                band_low: res.task1.feedback.band_low,
                band_high: res.task1.feedback.band_high,
                criteria: res.task1.feedback.criteria,
                limits: res.task1.feedback.limits,
              },
            },
            task2: {
              word_count: res.task2.word_count,
              min_words: res.task2.min_words,
              meets_minimum: res.task2.meets_minimum,
              feedback: {
                band_low: res.task2.feedback.band_low,
                band_high: res.task2.feedback.band_high,
                criteria: res.task2.feedback.criteria,
                limits: res.task2.feedback.limits,
              },
            },
            writing_band_low: res.writing_band_low,
            writing_band_high: res.writing_band_high,
          },
        });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Could not submit.";
        submittedRef.current = false;
        setError(message);
        // The server marks an expired writing section itself and moves
        // the mock to speaking — follow it there.
        if (message.toLowerCase().includes("expired")) {
          onAdvance();
        }
      } finally {
        setSubmitting(false);
      }
    },
    [mockId, task1, task2, task1Text, task2Text, submitting, clockStart, onAdvance],
  );

  const submitRef = useRef(submit);
  submitRef.current = submit;

  const remaining = useCountdown(
    clockStart,
    clockStart !== null && !result,
    useCallback(() => {
      void submitRef.current(true);
    }, []),
  );
  remainingRef.current = remaining;

  if (error && prompts.length === 0) return <p className="error">{error}</p>;
  if (prompts.length === 0) return <p>Loading…</p>;
  if (!task1 || !task2) {
    return (
      <p className="error">
        Could not find this mock&apos;s writing prompts. Start a new mock
        from the mock list.
      </p>
    );
  }

  if (result) {
    const taskBlock = (
      label: string,
      task: MockWritingSubmitResult["task1"],
    ) => (
      <section className="card" key={label}>
        <h2>{label}</h2>
        <p>
          {task.word_count} words —{" "}
          {task.meets_minimum ? "meets the minimum" : "below the minimum"}{" "}
          ({task.min_words} required). Band{" "}
          {task.feedback.band_low.toFixed(1)}–
          {task.feedback.band_high.toFixed(1)} <BandLabel />
        </p>
        {Object.entries(task.feedback.criteria).map(([key, crit]) => (
          <div key={key}>
            <h3>
              {CRITERION_LABELS[key] ?? key} — Band{" "}
              {crit.band_low.toFixed(1)}–{crit.band_high.toFixed(1)}
            </h3>
            <ul>
              {crit.notes.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </div>
        ))}
      </section>
    );
    return (
      <>
        <section className="card">
          <h1>Writing — submitted</h1>
          <p>
            Writing band{" "}
            <strong>
              {result.writing_band_low.toFixed(1)}–
              {result.writing_band_high.toFixed(1)}
            </strong>{" "}
            <BandLabel />
          </p>
          <p className="meta">{result.task1.feedback.limits}</p>
        </section>
        {taskBlock("Task 1", result.task1)}
        {taskBlock("Task 2", result.task2)}
        <p>
          <button onClick={onAdvance}>Continue to Speaking</button>
        </p>
      </>
    );
  }

  function taskEditor(
    label: string,
    prompt: WritingPromptSummary,
    text: string,
    setText: (v: string) => void,
  ) {
    const words = wordCount(text);
    return (
      <section className="card">
        <h2>
          {label}: {prompt.title}
        </h2>
        <p className="meta">
          At least {prompt.min_words} words · suggested{" "}
          {prompt.suggested_minutes} minutes
        </p>
        <p style={{ whiteSpace: "pre-wrap" }}>{prompt.prompt}</p>
        <label htmlFor={`mock-${label}-answer`}>Your answer</label>
        <textarea
          id={`mock-${label}-answer`}
          className="writing-box"
          value={text}
          disabled={submitting}
          onChange={(e) => setText(e.target.value)}
          rows={12}
        />
        <p className="wordcount">
          {words} / {prompt.min_words} words{" "}
          {words >= prompt.min_words ? (
            <span className="badge">Minimum reached</span>
          ) : (
            <span className="badge gold">
              {prompt.min_words - words} more to reach the minimum
            </span>
          )}
        </p>
      </section>
    );
  }

  return (
    <>
      <section className="hero">
        <h1>Writing</h1>
        <p className="lead">
          One 60-minute session: Task 1 and Task 2 together. The session
          auto-submits at 0, and you cannot go back once it is submitted.
        </p>
        {remaining !== null && (
          <p className="timer">
            Time left: <strong>{formatTime(remaining)}</strong>
          </p>
        )}
      </section>
      {error && <p className="error">{error}</p>}
      {taskEditor("Task 1", task1, task1Text, setTask1Text)}
      {taskEditor("Task 2", task2, task2Text, setTask2Text)}
      <p>
        <button onClick={() => void submit(false)} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit both tasks"}
        </button>
      </p>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Speaking section: same on-device recording + fluency flow as the    */
/* practice page, then the mock's speaking/complete endpoint.          */
/* ------------------------------------------------------------------ */

type SpeakingPhase = "idle" | "prep" | "talk" | "done";

function SpeakingSection({
  mockId,
  onAdvance,
}: {
  mockId: number;
  onAdvance: () => void;
}) {
  const [sets, setSets] = useState<SpeakingSet[]>([]);
  const [setId, setSetId] = useState("");
  const [error, setError] = useState("");
  const [phase, setPhase] = useState<SpeakingPhase>("idle");
  const [prepLeft, setPrepLeft] = useState(60);
  const [talkLeft, setTalkLeft] = useState(120);
  const [completing, setCompleting] = useState(false);
  const [completedNoBand, setCompletedNoBand] = useState(false);
  const startedAtRef = useRef<number | null>(null);

  const [recordingSupported] = useState(
    () =>
      typeof MediaRecorder !== "undefined" &&
      typeof navigator !== "undefined" &&
      !!navigator.mediaDevices?.getUserMedia,
  );
  const [recording, setRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const fluencyTrackerRef = useRef<FluencyTracker | null>(null);
  const [lastRecording, setLastRecording] = useState<{
    blob: Blob;
    mimeType: string;
    durationSeconds: number;
    fluency: FluencyEstimate | null;
  } | null>(null);

  useEffect(() => {
    api
      .speakingSets()
      .then((list) => {
        setSets(list);
        setSetId(list[0]?.id ?? "");
      })
      .catch(() => setError("Could not load the speaking sets."));
  }, []);

  const set = sets.find((s) => s.id === setId);

  useEffect(() => {
    if (phase !== "prep") return;
    const timer = window.setInterval(() => {
      setPrepLeft((prev) => {
        if (prev <= 1) {
          window.clearInterval(timer);
          setPhase("talk");
          setTalkLeft(set?.part2.talk_seconds ?? 120);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [phase, set]);

  useEffect(() => {
    if (phase !== "talk") return;
    const timer = window.setInterval(() => {
      setTalkLeft((prev) => {
        if (prev <= 1) {
          window.clearInterval(timer);
          setPhase("done");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [phase]);

  useEffect(
    () => () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  function pickSet(id: string) {
    setSetId(id);
    setPhase("idle");
    setAudioUrl(null);
    setLastRecording(null);
    setCompletedNoBand(false);
    startedAtRef.current = null;
  }

  function startPart2() {
    if (!set) return;
    if (!startedAtRef.current) startedAtRef.current = Date.now();
    setPrepLeft(set.part2.prep_seconds);
    setPhase("prep");
  }

  async function startRecording() {
    if (!recordingSupported) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      streamRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      fluencyTrackerRef.current = createFluencyTracker(
        stream,
        set?.part2.talk_seconds ?? 120,
      );
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        const fluency = fluencyTrackerRef.current?.stop() ?? null;
        fluencyTrackerRef.current = null;
        setLastRecording({
          blob,
          mimeType: recorder.mimeType || "audio/webm",
          durationSeconds: Math.max(
            1,
            Math.round(
              ((Date.now() - (startedAtRef.current ?? Date.now())) / 1000),
            ),
          ),
          fluency,
        });
        setAudioUrl((old) => {
          if (old) URL.revokeObjectURL(old);
          return URL.createObjectURL(blob);
        });
        stream.getTracks().forEach((t) => t.stop());
      };
      recorder.start();
      setRecording(true);
    } catch {
      setError(
        "Could not access the microphone. Check your browser permission and try again.",
      );
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function completeSpeaking() {
    if (!set || completing) return;
    setCompleting(true);
    setError("");
    const duration = startedAtRef.current
      ? Math.round((Date.now() - startedAtRef.current) / 1000)
      : 0;
    try {
      // Keep the recording on this device, as the practice page does.
      if (lastRecording) {
        try {
          await saveSpeakingRecording({
            setId: set.id,
            topic: set.topic,
            part: "Part 2",
            durationSeconds: lastRecording.durationSeconds,
            blob: lastRecording.blob,
            mimeType: lastRecording.mimeType,
            fluency: lastRecording.fluency,
          });
        } catch {
          /* Recording history is a bonus; the mock still completes. */
        }
      }
      const fluency = lastRecording?.fluency ?? null;
      await api.completeMockSpeaking(
        mockId,
        set.id,
        duration,
        fluency?.bandLow,
        fluency?.bandHigh,
      );
      // A banded speaking section moves the mock to "done" even when
      // the overall band is still null (e.g. writing expired), so
      // re-read the mock instead of trusting the overall band.
      const detail = await api.getMock(mockId);
      if (detail.current_section === "done" || detail.status === "complete") {
        onAdvance();
      } else {
        // No fluency range was available, so the mock has no speaking
        // band yet and stays open on this section.
        setCompletedNoBand(true);
        setPhase("idle");
        setAudioUrl(null);
        setLastRecording(null);
        startedAtRef.current = null;
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not complete the speaking section.",
      );
    } finally {
      setCompleting(false);
    }
  }

  if (!set) return <p>Loading…</p>;

  return (
    <>
      <section className="hero">
        <h1>Speaking</h1>
        <p className="lead">
          The last section, and a separate slot — no clock is running.
          Part 1 questions, a Part 2 cue card with one minute to prepare
          and two minutes to talk, then Part 3 discussion. Your recording
          stays on your device — nothing is uploaded.
        </p>
        <p>
          <label htmlFor="mock-speaking-set">Choose a topic</label>{" "}
          <select
            id="mock-speaking-set"
            value={setId}
            onChange={(e) => pickSet(e.target.value)}
          >
            {sets.map((s) => (
              <option key={s.id} value={s.id}>
                {s.topic}
              </option>
            ))}
          </select>
        </p>
      </section>

      {error && <p className="error">{error}</p>}
      {completedNoBand && (
        <p className="notice">
          Speaking is saved, but no fluency range could be measured from
          your recording, so there is no speaking band yet and no overall
          band. Record a talk with the microphone to get a fluency range,
          then complete this section again.
        </p>
      )}

      <section className="card">
        <h2>Part 1 — Introduction and interview</h2>
        <p>Answer each question in a few sentences, out loud.</p>
        <ol>
          {set.part1.map((q, i) => (
            <li key={i}>{q}</li>
          ))}
        </ol>
      </section>

      <section className="card">
        <h2>Part 2 — Long turn</h2>
        <div className="cue-card">
          <p>
            <strong>{set.part2.cue}</strong>
          </p>
          <p>You should say:</p>
          <ul>
            {set.part2.points.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
        {phase === "idle" && (
          <p>
            <button onClick={startPart2}>Start 1-minute preparation</button>
          </p>
        )}
        {phase === "prep" && (
          <p className="timer">
            Preparation time left: <strong>{formatTime(prepLeft)}</strong> —
            make notes, then talk.
          </p>
        )}
        {(phase === "talk" || phase === "done") && (
          <>
            <p className="timer">
              Talk time left: <strong>{formatTime(talkLeft)}</strong>
            </p>
            {phase === "talk" && (
              <p>
                <button onClick={() => setPhase("done")}>
                  Finish talking
                </button>
              </p>
            )}
          </>
        )}
        <h3>Record yourself</h3>
        {!recordingSupported ? (
          <p className="notice">
            This browser does not support recording. You can still practise
            out loud without a recording, but no fluency range can be
            measured.
          </p>
        ) : recording ? (
          <p>
            <button className="secondary" onClick={stopRecording}>
              Stop recording
            </button>{" "}
            Recording… speak for up to two minutes.
          </p>
        ) : (
          <p>
            <button onClick={() => void startRecording()}>
              {audioUrl ? "Re-record" : "Record my talk"}
            </button>
          </p>
        )}
        {audioUrl && (
          <p>
            <audio controls src={audioUrl} />
          </p>
        )}
        {lastRecording?.fluency && (
          <p>
            Fluency range from your recording: Band{" "}
            {lastRecording.fluency.bandLow.toFixed(1)}–
            {lastRecording.fluency.bandHigh.toFixed(1)}{" "}
            <span className="band-label">{BAND_LABEL}</span>
          </p>
        )}
        {set.sample_answer && (
          <details>
            <summary>Read a sample talk</summary>
            <p style={{ whiteSpace: "pre-wrap" }}>{set.sample_answer}</p>
          </details>
        )}
      </section>

      <section className="card">
        <h2>Part 3 — Two-way discussion</h2>
        <ol>
          {set.part3.map((q, i) => (
            <li key={i}>{q}</li>
          ))}
        </ol>
        <p>
          <button onClick={() => void completeSpeaking()} disabled={completing}>
            {completing ? "Saving…" : "Complete speaking and finish the mock"}
          </button>
        </p>
      </section>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Runner shell                                                        */
/* ------------------------------------------------------------------ */

export default function MockRunner() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const mockId = Number(id);

  const [mock, setMock] = useState<MockDetail | null>(null);
  const [plan, setPlan] = useState<MockPlan | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!Number.isFinite(mockId) || mockId <= 0) return;
    try {
      const detail = await api.getMock(mockId);
      setMock(detail);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load this mock.",
      );
    }
  }, [mockId]);

  useEffect(() => {
    if (!user || !Number.isFinite(mockId) || mockId <= 0) {
      setLoading(false);
      return;
    }
    // Plan from the start response (passed via navigation state), from
    // this device's storage, or re-derived from the mock rotation.
    const statePlan = (
      location.state as { plan?: MockStartResponse } | null
    )?.plan;
    void (async () => {
      setLoading(true);
      try {
        const detail = await api.getMock(mockId);
        setMock(detail);
        if (statePlan) {
          saveMockPlan(mockId, statePlan);
          setPlan(statePlan);
        } else {
          const stored = loadMockPlan(mockId);
          if (stored) {
            setPlan(stored);
          } else {
            const [mocks, prompts] = await Promise.all([
              api.listMocks(),
              api.writingPrompts(detail.track as MockTrack),
            ]);
            setPlan(
              deriveMockPlan(mockId, detail.track as MockTrack, mocks, prompts),
            );
          }
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not load this mock.",
        );
      } finally {
        setLoading(false);
      }
    })();
  }, [user, mockId, location.state]);

  if (authLoading || loading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Full mock</h1>
        <p>Log in to take a full mock.</p>
        <Link className="btn" to="/login">
          Log in
        </Link>
      </section>
    );
  }
  if (!Number.isFinite(mockId) || mockId <= 0) {
    return <p className="error">That mock does not exist.</p>;
  }
  if (error && !mock) return <p className="error">{error}</p>;
  if (!mock) return <p>Loading…</p>;

  if (mock.current_section === "done" || mock.status === "complete") {
    return (
      <section className="card">
        <h1>Mock complete</h1>
        {mock.overall_band !== null ? (
          <p>
            Overall band{" "}
            <strong>{mock.overall_band.toFixed(1)}</strong>{" "}
            <BandLabel />
          </p>
        ) : (
          <p>
            This mock is finished, but there is no overall band — a
            section expired before it could be scored. The sections that
            were scored still show their bands on the results page.
          </p>
        )}
        <p>
          <Link className="btn" to={`/mock/${mock.mock_id}/results`}>
            See your results
          </Link>{" "}
          <Link className="btn secondary" to="/mock">
            Back to mocks
          </Link>
        </p>
      </section>
    );
  }

  if (!plan) {
    return (
      <section className="card">
        <h1>Full mock</h1>
        <p className="error">
          Could not work out which test this mock uses. Start a new mock
          from the mock list.
        </p>
        <Link className="btn" to="/mock">
          Back to mocks
        </Link>
      </section>
    );
  }

  const onAdvance = () => {
    void refresh();
  };

  return (
    <>
      <ProgressStrip mock={mock} />
      {error && <p className="error">{error}</p>}
      {mock.current_section === "listening" && (
        <ScoredSection
          mockId={mock.mock_id}
          kind="listening"
          testId={plan.listening_test_id}
          expiresAt={mock.section_expires_at}
          onAdvance={onAdvance}
        />
      )}
      {mock.current_section === "reading" && (
        <ScoredSection
          mockId={mock.mock_id}
          kind="reading"
          testId={plan.reading_test_id}
          expiresAt={mock.section_expires_at}
          onAdvance={onAdvance}
        />
      )}
      {mock.current_section === "writing" && (
        <WritingSection
          mockId={mock.mock_id}
          track={mock.track as MockTrack}
          plan={plan}
          expiresAt={mock.section_expires_at}
          onAdvance={onAdvance}
        />
      )}
      {mock.current_section === "speaking" && (
        <SpeakingSection mockId={mock.mock_id} onAdvance={onAdvance} />
      )}
      <p>
        <button
          className="secondary"
          onClick={() => navigate(`/mock/${mock.mock_id}/results`)}
        >
          View results so far
        </button>
      </p>
    </>
  );
}
