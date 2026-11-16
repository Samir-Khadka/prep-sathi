import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import {
  api,
  type ReadingTest,
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

export default function ReadingTestPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const { user, loading: authLoading } = useAuth();
  const mode = ((location.state as { mode?: TestMode } | null)?.mode ??
    "practice") as TestMode;

  const [test, setTest] = useState<ReadingTest | null>(null);
  const [session, setSession] = useState<TestSession | null>(null);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittedRef = useRef(false);

  useEffect(() => {
    if (!id || !user) return;
    api
      .readingTest(id)
      .then(setTest)
      .catch(() => setError("Could not load this test."));
    api
      .startReading(id, mode)
      .then(setSession)
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
      const res = await api.submitReading(id, session.session_id, payload);
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
        <h1>Reading test</h1>
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
          {test.track === "academic" ? "Academic" : "General Training"} ·{" "}
          {mode === "timed"
            ? "Timed mock — the test auto-submits when the timer ends."
            : "Practice mode — no time limit."}
        </p>
        {mode === "timed" && remaining !== null && (
          <p className="timer">
            Time left: <strong>{formatTime(remaining)}</strong>
          </p>
        )}
      </section>

      {error && <p className="error">{error}</p>}

      {test.passages.map((passage) => (
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
          {submitting ? "Submitting…" : "Submit answers"}
        </button>
      </p>
    </>
  );
}
