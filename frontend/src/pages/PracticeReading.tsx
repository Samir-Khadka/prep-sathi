import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type ReadingTestSummary, type TestMode } from "../api";
import { useAuth } from "../auth";
import { formatTime } from "./practiceShared";

export default function PracticeReading() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [track, setTrack] = useState<"academic" | "general">("academic");
  const [tests, setTests] = useState<ReadingTestSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .readingTests(track)
      .then(setTests)
      .catch(() => setError("Could not load the reading tests."));
  }, [track]);

  function start(test: ReadingTestSummary, mode: TestMode) {
    navigate(`/practice/reading/${test.id}`, { state: { mode } });
  }

  return (
    <>
      <section className="hero">
        <h1>Reading practice</h1>
        <p className="lead">
          Three passages, 40 questions, 60 minutes in timed mode. Timed
          mode enforces the real timing; practice mode has no time limit.
          Every band is a practice estimate, not an official score.
        </p>
        <p>
          <label htmlFor="track">Track</label>
          <select
            id="track"
            value={track}
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
      {!user && (
        <p className="notice">
          <Link to="/login">Log in</Link> to start a test and record your
          band on the dashboard.
        </p>
      )}
      {tests.length === 0 && !error ? (
        <p>Loading…</p>
      ) : (
        <div className="grid">
          {tests.map((t) => (
            <article key={t.id} className="card module-card">
              <h3>{t.title}</h3>
              <p className="meta">
                {t.total_questions} questions · timed limit{" "}
                {formatTime(t.time_limit_seconds)}
              </p>
              {t.passages && (
                <ul className="clean">
                  {t.passages.map((p) => (
                    <li key={p.section}>
                      Section {p.section}: {p.title} ({p.question_count}{" "}
                      questions)
                    </li>
                  ))}
                </ul>
              )}
              <p>
                <button onClick={() => start(t, "timed")}>Timed mock</button>{" "}
                <button
                  className="secondary"
                  onClick={() => start(t, "practice")}
                >
                  Practice mode
                </button>
              </p>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
