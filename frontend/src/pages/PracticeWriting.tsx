import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type WritingPrompt,
  type WritingPromptSummary,
  type WritingSubmitResult,
} from "../api";
import { useAuth } from "../auth";
import { formatTime, useCountdown } from "./practiceShared";

const SESSION_SECONDS = 3600;

function wordCount(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean);
  return text.trim() === "" ? 0 : words.length;
}

export default function PracticeWriting() {
  const { user, loading: authLoading } = useAuth();
  const [track, setTrack] = useState<"academic" | "general">("academic");
  const [prompts, setPrompts] = useState<WritingPromptSummary[]>([]);
  const [task1Id, setTask1Id] = useState("");
  const [task2Id, setTask2Id] = useState("");
  const [task1Text, setTask1Text] = useState("");
  const [task2Text, setTask2Text] = useState("");
  const [started, setStarted] = useState(false);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [results, setResults] = useState<{
    task1?: WritingSubmitResult;
    task2?: WritingSubmitResult;
  }>({});
  const [full, setFull] = useState<{
    task1?: WritingPrompt;
    task2?: WritingPrompt;
  }>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittedRef = useRef(false);

  useEffect(() => {
    api
      .writingPrompts(track)
      .then((list) => {
        setPrompts(list);
        setTask1Id(list.find((p) => p.task === 1)?.id ?? "");
        setTask2Id(list.find((p) => p.task === 2)?.id ?? "");
        setStarted(false);
        setSubmitted(false);
        setResults({});
        setFull({});
        setTask1Text("");
        setTask2Text("");
      })
      .catch(() => setError("Could not load the writing prompts."));
  }, [track]);

  const task1 = useMemo(
    () => prompts.find((p) => p.id === task1Id),
    [prompts, task1Id],
  );
  const task2 = useMemo(
    () => prompts.find((p) => p.id === task2Id),
    [prompts, task2Id],
  );

  async function submitBoth() {
    if (!task1 || !task2 || submittedRef.current || submitting) return;
    submittedRef.current = true;
    setSubmitting(true);
    const duration = startedAt
      ? Math.round((Date.now() - startedAt) / 1000)
      : 0;
    try {
      const [r1, r2, f1, f2] = await Promise.all([
        api.submitWriting(task1.id, task1Text, duration),
        api.submitWriting(task2.id, task2Text, duration),
        api.writingPrompt(task1.id),
        api.writingPrompt(task2.id),
      ]);
      setResults({ task1: r1, task2: r2 });
      setFull({ task1: f1, task2: f2 });
      setSubmitted(true);
    } catch (err) {
      submittedRef.current = false;
      setError(
        err instanceof Error ? err.message : "Could not submit your writing.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const submitRef = useRef(submitBoth);
  submitRef.current = submitBoth;

  const remaining = useCountdown(
    started && !submitted ? SESSION_SECONDS : null,
    started && !submitted,
    () => {
      void submitRef.current();
    },
  );

  if (authLoading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Writing practice</h1>
        <p>Log in to write and save your attempts.</p>
        <Link className="btn" to="/login">
          Log in
        </Link>
      </section>
    );
  }

  function startSession() {
    if (!task1 || !task2) return;
    setStarted(true);
    setStartedAt(Date.now());
  }

  function taskBlock(
    label: string,
    prompt: WritingPromptSummary | undefined,
    text: string,
    setText: (v: string) => void,
    result: WritingSubmitResult | undefined,
    fullPrompt: WritingPrompt | undefined,
  ) {
    if (!prompt) return null;
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
        <label htmlFor={`${label}-answer`}>Your answer</label>
        <textarea
          id={`${label}-answer`}
          className="writing-box"
          value={text}
          disabled={!started || submitted}
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
        {submitted && result && fullPrompt && (
          <>
            <p>
              <strong>Submitted:</strong> {result.word_count} words —{" "}
              {result.meets_minimum
                ? "meets the minimum"
                : "below the minimum"}{" "}
              ({result.min_words} required).
            </p>
            <h3>Model answer</h3>
            <p style={{ whiteSpace: "pre-wrap" }}>
              {fullPrompt.model_answer}
            </p>
            <h3>What makes this strong</h3>
            <p>{fullPrompt.commentary}</p>
          </>
        )}
      </section>
    );
  }

  return (
    <>
      <section className="hero">
        <h1>Writing practice</h1>
        <p className="lead">
          One 60-minute session: a Task 1 prompt and a Task 2 prompt. Model
          answers and commentary are revealed only after you submit both.
          Writing is not auto-scored — there is no band estimate here,
          because no automated feedback is given in Phase 2.
        </p>
        <p>
          <label htmlFor="track">Track</label>
          <select
            id="track"
            value={track}
            disabled={started}
            onChange={(e) =>
              setTrack(e.target.value as "academic" | "general")
            }
          >
            <option value="academic">Academic</option>
            <option value="general">General Training</option>
          </select>
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      {!started ? (
        <section className="card">
          <h2>Choose your prompts</h2>
          <label htmlFor="task1">Task 1 (at least 150 words)</label>
          <select
            id="task1"
            value={task1Id}
            onChange={(e) => setTask1Id(e.target.value)}
          >
            {prompts
              .filter((p) => p.task === 1)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title} — {p.suggested_minutes} min
                </option>
              ))}
          </select>
          <label htmlFor="task2">Task 2 (at least 250 words)</label>
          <select
            id="task2"
            value={task2Id}
            onChange={(e) => setTask2Id(e.target.value)}
          >
            {prompts
              .filter((p) => p.task === 2)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title} — {p.suggested_minutes} min
                </option>
              ))}
          </select>
          <p>
            <button onClick={startSession} disabled={!task1 || !task2}>
              Start 60-minute session
            </button>
          </p>
        </section>
      ) : (
        <>
          {remaining !== null && !submitted && (
            <p className="timer">
              Time left: <strong>{formatTime(remaining)}</strong> — the
              session auto-submits at 0.
            </p>
          )}
          {taskBlock(
            "Task 1",
            task1,
            task1Text,
            setTask1Text,
            results.task1,
            full.task1,
          )}
          {taskBlock(
            "Task 2",
            task2,
            task2Text,
            setTask2Text,
            results.task2,
            full.task2,
          )}
          {!submitted && (
            <p>
              <button onClick={() => void submitBoth()} disabled={submitting}>
                {submitting ? "Submitting…" : "Submit both tasks"}
              </button>
            </p>
          )}
          {submitted && (
            <p className="notice">
              Saved. Compare your writing with the model answers above, then
              try another pair of prompts.
            </p>
          )}
        </>
      )}
    </>
  );
}
