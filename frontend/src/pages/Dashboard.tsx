import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Dashboard } from "../api";
import { useAuth } from "../auth";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    api.dashboard().then(setData).catch(() => {
      setError("Could not load your progress. Please try again later.");
    });
  }, [user]);

  if (loading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Your dashboard</h1>
        <p>Log in to see your progress.</p>
        <Link className="btn" to="/login">
          Log in
        </Link>
      </section>
    );
  }

  return (
    <>
      <section className="hero">
        <h1>Namaste, {user.name || user.email}</h1>
        <p className="lead">
          Your target:{" "}
          {user.target_band_overall
            ? `band ${user.target_band_overall} overall`
            : "no target set"}
          {user.target_band_writing
            ? `, ${user.target_band_writing} in Writing`
            : ""}
          .
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      {data && (
        <section className="card">
          <div className="stat-row">
            <div className="stat">
              <div className="num">{data.attempts_total}</div>
              <div className="lbl">Attempts completed</div>
            </div>
            <div className="stat">
              <div className="num">{data.vocabulary_total}</div>
              <div className="lbl">Words in your list</div>
            </div>
            <div className="stat">
              <div className="num">{data.vocabulary_due}</div>
              <div className="lbl">Words due for review</div>
            </div>
          </div>
          <h2>Attempts by module</h2>
          {Object.keys(data.attempts_by_module).length === 0 ? (
            <p>No attempts yet. Practice content arrives in Phase 2.</p>
          ) : (
            <ul className="clean">
              {Object.entries(data.attempts_by_module).map(
                ([module, count]) => (
                  <li key={module}>
                    <strong>{module}</strong> — {count} attempt
                    {count === 1 ? "" : "s"}
                  </li>
                ),
              )}
            </ul>
          )}
          <p>
            <Link to="/vocabulary">Review your vocabulary →</Link>
          </p>
        </section>
      )}
    </>
  );
}
