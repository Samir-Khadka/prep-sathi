import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type MockSummary, type MockTrack } from "../api";
import { useAuth } from "../auth";
import { BandLabel } from "./practiceShared";
import { saveMockPlan } from "./mockPlan";

function statusLabel(mock: MockSummary): string {
  if (mock.status === "complete") return "Complete";
  if (mock.current_section === "done") return "Finished";
  return `In progress — ${mock.current_section}`;
}

export default function MockList() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [track, setTrack] = useState<MockTrack>("academic");
  const [mocks, setMocks] = useState<MockSummary[]>([]);
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!user) return;
    api
      .listMocks()
      .then(setMocks)
      .catch(() => setError("Could not load your past mocks."));
  }, [user]);

  if (authLoading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Full mock</h1>
        <p>Log in to take a full mock and keep your results.</p>
        <Link className="btn" to="/login">
          Log in
        </Link>
      </section>
    );
  }

  async function startMock() {
    setError("");
    setStarting(true);
    try {
      const started = await api.startMock(track);
      saveMockPlan(started.mock_id, started);
      navigate(`/mock/${started.mock_id}`, {
        state: { plan: started },
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not start the mock.",
      );
    } finally {
      setStarting(false);
    }
  }

  const inProgress = mocks.find((m) => m.status === "in_progress");

  return (
    <>
      <section className="hero">
        <h1>Full mock</h1>
        <p className="lead">
          A complete test in one sitting, in test order: Listening (about
          32 minutes), then Reading (60 minutes), then Writing (60
          minutes, Task 1 and Task 2 together). Speaking is a separate
          slot — you take it after Writing, with no clock running.
        </p>
        <p>
          There are no breaks and no going back: once a section is
          submitted it is closed. If a section runs out of time it is
          marked expired and the mock moves on, so a missed section never
          blocks the rest. Every band is a{" "}
          <BandLabel />.
        </p>
        <p>
          <label htmlFor="mock-track">Track</label>{" "}
          <select
            id="mock-track"
            value={track}
            onChange={(e) => setTrack(e.target.value as MockTrack)}
          >
            <option value="academic">Academic</option>
            <option value="general">General Training</option>
          </select>
        </p>
        {inProgress && (
          <p className="notice">
            You have a mock in progress ({inProgress.track},{" "}
            {inProgress.current_section}). Starting a new one leaves the
            old one where it is — you can return to it from the list
            below.{" "}
            <Link to={`/mock/${inProgress.mock_id}`}>Resume it</Link>
          </p>
        )}
        <p>
          <button onClick={() => void startMock()} disabled={starting}>
            {starting ? "Starting…" : "Start full mock"}
          </button>
        </p>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <h2>Your mocks</h2>
        {mocks.length === 0 ? (
          <p>No mocks yet. Your first full mock is the best way to see where you stand.</p>
        ) : (
          <table className="attempts">
            <thead>
              <tr>
                <th>Started</th>
                <th>Track</th>
                <th>Status</th>
                <th>Overall band</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {mocks.map((mock) => (
                <tr key={mock.mock_id}>
                  <td>
                    {new Date(mock.started_at).toLocaleString(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </td>
                  <td>
                    {mock.track === "academic"
                      ? "Academic"
                      : "General Training"}
                  </td>
                  <td>{statusLabel(mock)}</td>
                  <td>
                    {mock.overall_band !== null ? (
                      <>
                        Band {mock.overall_band.toFixed(1)}{" "}
                        <BandLabel />
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>
                    {mock.status === "complete" ? (
                      <Link to={`/mock/${mock.mock_id}/results`}>
                        Results
                      </Link>
                    ) : (
                      <Link to={`/mock/${mock.mock_id}`}>Resume</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </>
  );
}
