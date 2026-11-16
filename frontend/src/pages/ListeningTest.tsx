import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import {
  api,
  type ListeningTest,
  type SubmitResult,
  type TestMode,
  type TestSession,
} from "../api";
import { useAuth } from "../auth";
import {
  formatTime,
  QuestionInput,
  ResultsView,
  useCountdown,
  type AnswerValue,
} from "./practiceShared";

export default function ListeningTestPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const { user, loading: authLoading } = useAuth();
  const mode = ((location.state as { mode?: TestMode } | null)?.mode ??
    "practice") as TestMode;

  const [test, setTest] = useState<ListeningTest | null>(null);
  const [session, setSession] = useState<TestSession | null>(null);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const startedAtRef = useRef<number>(Date.now());
  const submittedRef = useRef(false);

  useEffect(() => {
    if (!id || !user) return;
    api
      .listeningTest(id)
      .then(setTest)
      .catch(() => setError("Could not load this test."));
    api
      .startListening(id, mode)
      .then((s) => {
        setSession(s);
        startedAtRef.current = Date.parse(s.started_at) || Date.now();
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Could not start the test."),
      );
  }, [id, user, mode]);

  const submit = useCallback(async () => {
    if (!id || !session || submittedRef.current || submitting) return;
    submittedRef.current = true;
    setSubmitting(true);
    const payload: Record<string, string | number> = {};
    for (const [k, v] of Object.entries(answers)) {
      if (v !== undefined && v !== "") payload[k] = v;
    }
    try {
      const res = await api.submitListening(id, session.session_id, payload);
      setResult(res);
    } catch (err) {
      submittedRef.current = false;
      setError(
        err instanceof Error ? err.message : "Could not submit your answers.",
      );
    } finally {
      setSubmitting(false);
    }
  }, [id, session, answers, submitting]);

  const submitRef = useRef(submit);
  submitRef.current = submit;

  const remaining = useCountdown(
    mode === "timed" ? (session?.time_limit_seconds ?? null) : null,
    mode === "timed" && !!session && !result,
    useCallback(() => {
      void submitRef.current();
    }, []),
  );

  if (authLoading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Listening test</h1>
        <p>Log in to take this test.</p>
        <Link className="btn" to="/login">
          Log in
        </Link>
      </section>
    );
  }
  if (error && !test) return <p className="error">{error}</p>;
  if (!test || !session) return <p>Loading…</p>;
  if (result) return <ResultsView result={result} title={test.title} />;

  function setAnswer(no: number, value: string | number) {
    setAnswers((prev) => ({ ...prev, [String(no)]: value }));
  }

  return (
    <>
      <section className="hero">
        <h1>{test.title}</h1>
        <p className="lead">
          {mode === "timed"
            ? "Timed mock — the test auto-submits when the timer ends."
            : "Practice mode — no time limit."}{" "}
          Read each transcript once, as you would hear it once.
        </p>
        {mode === "timed" && remaining !== null && (
          <p className="timer">
            Time left: <strong>{formatTime(remaining)}</strong>
          </p>
        )}
      </section>

      {error && <p className="error">{error}</p>}

      {test.parts.map((part) => (
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

      <p>
        <button onClick={() => void submit()} disabled={submitting}>
          {submitting ? "Submitting…" : "Submit answers"}
        </button>
      </p>
    </>
  );
}
