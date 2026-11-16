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
            <p>No attempts yet. Start with a practice test below.</p>
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
            <Link to="/practice/listening">Listening practice →</Link> ·{" "}
            <Link to="/practice/reading">Reading practice →</Link> ·{" "}
            <Link to="/practice/writing">Writing practice →</Link> ·{" "}
            <Link to="/practice/speaking">Speaking practice →</Link>
          </p>
        </section>
      )}

      {data && data.latest_band_by_module && (
        <section className="card">
          <h2>Latest band by module</h2>
          <p className="honesty">
            Every band below is a practice estimate, not an official score.
          </p>
          <div className="stat-row">
            {["listening", "reading", "writing", "speaking"].map((m) => (
              <div className="stat" key={m}>
                <div className="num">
                  {data.latest_band_by_module?.[m] != null
                    ? `Band ${Number(data.latest_band_by_module[m]).toFixed(1)}`
                    : "—"}
                </div>
                <div className="lbl">{m}</div>
              </div>
            ))}
          </div>
          <p>
            <strong>Overall estimate: </strong>
            {data.overall_estimate != null
              ? `Band ${data.overall_estimate.toFixed(1)}`
              : "— (complete all four modules for an overall estimate)"}
            {data.target_band_overall != null && (
              <>
                {" "}
                vs your target of band {data.target_band_overall}
              </>
            )}
            . <span className="band-label">practice estimate, not an official score</span>
          </p>
        </section>
      )}

      {data && data.attempts_recent && data.attempts_recent.length > 0 && (
        <section className="card">
          <h2>Recent attempts</h2>
          <table className="attempts">
            <thead>
              <tr>
                <th>Module</th>
                <th>Kind</th>
                <th>Raw</th>
                <th>Band</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {data.attempts_recent.map((a) => (
                <tr key={a.id}>
                  <td>{a.module}</td>
                  <td>{a.kind}</td>
                  <td>{a.score_raw ?? "—"}</td>
                  <td>
                    {a.band_estimate != null
                      ? `Band ${a.band_estimate.toFixed(1)}`
                      : "—"}
                  </td>
                  <td>{new Date(a.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="honesty">
            Bands are practice estimates, not official scores.
          </p>
        </section>
      )}
    </>
  );
}
