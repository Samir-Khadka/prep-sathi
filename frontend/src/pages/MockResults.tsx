import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type MockDetail } from "../api";
import { useAuth } from "../auth";
import { BandLabel, ResultsView } from "./practiceShared";
import { loadMockResults, type StoredMockResults } from "./mockPlan";

const CRITERION_LABELS: Record<string, string> = {
  task_achievement: "Task achievement",
  coherence: "Coherence and cohesion",
  lexical: "Lexical resource",
  grammar: "Grammatical range and accuracy",
};

function band(value: number | null): string {
  return value === null ? "—" : `Band ${value.toFixed(1)}`;
}

export default function MockResults() {
  const { id } = useParams<{ id: string }>();
  const { user, loading: authLoading } = useAuth();
  const mockId = Number(id);
  const [mock, setMock] = useState<MockDetail | null>(null);
  const [stored, setStored] = useState<StoredMockResults>({});
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user || !Number.isFinite(mockId) || mockId <= 0) return;
    setStored(loadMockResults(mockId));
    api
      .getMock(mockId)
      .then(setMock)
      .catch((err: unknown) =>
        setError(
          err instanceof Error ? err.message : "Could not load this mock.",
        ),
      );
  }, [user, mockId]);

  if (authLoading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Mock results</h1>
        <p>Log in to see your mock results.</p>
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

  const { sections } = mock;
  const writing = stored.writing;

  return (
    <>
      <section className="card">
        <h1>
          Full mock results —{" "}
          {mock.track === "academic" ? "Academic" : "General Training"}
        </h1>
        <p className="meta">
          Started{" "}
          {new Date(mock.started_at).toLocaleString(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
          })}{" "}
          ·{" "}
          {mock.status === "complete"
            ? "Complete"
            : `In progress — ${mock.current_section}`}
        </p>
        <div className="stat-row">
          <div className="stat">
            <div className="num">
              {mock.overall_band !== null
                ? `Band ${mock.overall_band.toFixed(1)}`
                : "Pending"}
            </div>
            <div className="lbl">
              Overall band — <BandLabel />
            </div>
          </div>
        </div>
        {mock.overall_band === null && (
          <p className="notice">
            {sections.speaking.status === "done"
              ? "A section expired before it could be scored, so there is no overall band for this mock."
              : "Complete Speaking to see your overall estimate."}
          </p>
        )}
      </section>

      <section className="card">
        <h2>Listening</h2>
        <p>
          {sections.listening.score_raw !== null
            ? `${sections.listening.score_raw} / 40 correct — `
            : ""}
          {band(sections.listening.band_estimate)}{" "}
          <BandLabel />
          {sections.listening.status === "expired" &&
            " (section ran out of time)"}
        </p>
        {stored.listening && (
          <ResultsView
            result={{
              score_raw: stored.listening.score_raw,
              band_estimate: stored.listening.band_estimate,
              band_label: mock.band_label,
              duration_seconds: stored.listening.duration_seconds,
              overtime: sections.listening.status === "expired",
              results: stored.listening.results,
            }}
            title="Listening — question by question"
          />
        )}
      </section>

      <section className="card">
        <h2>Reading</h2>
        <p>
          {sections.reading.score_raw !== null
            ? `${sections.reading.score_raw} / 40 correct — `
            : ""}
          {band(sections.reading.band_estimate)}{" "}
          <BandLabel />
          {sections.reading.status === "expired" &&
            " (section ran out of time)"}
        </p>
        {stored.reading && (
          <ResultsView
            result={{
              score_raw: stored.reading.score_raw,
              band_estimate: stored.reading.band_estimate,
              band_label: mock.band_label,
              duration_seconds: stored.reading.duration_seconds,
              overtime: sections.reading.status === "expired",
              results: stored.reading.results,
            }}
            title="Reading — question by question"
          />
        )}
      </section>

      <section className="card">
        <h2>Writing</h2>
        <p>
          {sections.writing.band_low !== null &&
          sections.writing.band_high !== null ? (
            <>
              Band {sections.writing.band_low.toFixed(1)}–
              {sections.writing.band_high.toFixed(1)} <BandLabel />
            </>
          ) : (
            "No band yet"
          )}
          {sections.writing.status === "expired" &&
            " (section ran out of time)"}
        </p>
        {writing ? (
          <>
            {(
              [
                ["Task 1", writing.task1],
                ["Task 2", writing.task2],
              ] as const
            ).map(([label, task]) => (
              <div key={label}>
                <h3>
                  {label} — {task.word_count} words, Band{" "}
                  {task.feedback.band_low.toFixed(1)}–
                  {task.feedback.band_high.toFixed(1)}
                </h3>
                {Object.entries(task.feedback.criteria).map(
                  ([key, crit]) => (
                    <div key={key}>
                      <h4>
                        {CRITERION_LABELS[key] ?? key} — Band{" "}
                        {crit.band_low.toFixed(1)}–
                        {crit.band_high.toFixed(1)}
                      </h4>
                      <ul>
                        {crit.notes.map((note, i) => (
                          <li key={i}>{note}</li>
                        ))}
                      </ul>
                    </div>
                  ),
                )}
              </div>
            ))}
            <p className="meta">{writing.task1.feedback.limits}</p>
          </>
        ) : (
          sections.writing.status === "done" && (
            <p className="meta">
              Detailed per-criterion feedback was shown when you submitted
              Writing on this device.
            </p>
          )
        )}
      </section>

      <section className="card">
        <h2>Speaking</h2>
        <p>
          {sections.speaking.band_estimate !== null ? (
            <>
              {band(sections.speaking.band_estimate)} <BandLabel /> — from
              the on-device fluency range of your recorded talk (timing
              signals only).
            </>
          ) : (
            "No band yet — complete the Speaking section to add one."
          )}
        </p>
      </section>

      <p>
        {mock.status !== "complete" && mock.current_section !== "done" && (
          <>
            <Link className="btn" to={`/mock/${mock.mock_id}`}>
              Resume mock
            </Link>{" "}
          </>
        )}
        <Link className="btn secondary" to="/mock">
          Back to mocks
        </Link>
      </p>
    </>
  );
}
