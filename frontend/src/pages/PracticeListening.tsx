import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type ListeningTestSummary, type TestMode } from "../api";
import { useAuth } from "../auth";
import { formatTime } from "./practiceShared";

export default function PracticeListening() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [tests, setTests] = useState<ListeningTestSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listeningTests()
      .then(setTests)
      .catch(() => setError("Could not load the listening tests."));
  }, []);

  function start(test: ListeningTestSummary, mode: TestMode) {
    navigate(`/practice/listening/${test.id}`, { state: { mode } });
  }

  return (
    <>
      <section className="hero">
        <h1>Listening practice</h1>
        <p className="lead">
          Four parts, 40 questions, about 30 minutes in timed mode. Timed
          mode enforces the real timing; practice mode has no time limit.
          Every band is a practice estimate, not an official score.
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
              <ul className="clean">
                {t.parts.map((p) => (
                  <li key={p.part}>
                    Part {p.part}: {p.title} ({p.question_count} questions)
                    {p.has_audio ? "" : " — audio pending"}
                  </li>
                ))}
              </ul>
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
