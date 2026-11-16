import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type ModuleInfo } from "../api";

export default function Home() {
  const [modules, setModules] = useState<ModuleInfo[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.modules().then(setModules).catch(() => {
      setError("Could not reach the practice API. Please try again later.");
    });
  }, []);

  return (
    <>
      <section className="hero">
        <h1>Prepare for IELTS, free — on your phone.</h1>
        <p className="lead">
          PrepSathi is free IELTS-format practice for Nepali learners
          preparing for study abroad. Four modules, timed mocks, honest
          band estimates, and vocabulary that follows your mistakes. No
          paywall, no copied test books.
        </p>
        <p>
          <Link className="btn" to="/signup">
            Create a free account
          </Link>{" "}
          <Link className="btn secondary" to="/resources">
            Start with official free material
          </Link>
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      <div className="grid">
        {modules.map((m) => (
          <article key={m.slug} className="card module-card">
            <h3>{m.name}</h3>
            <p className="meta">
              {m.time_minutes} · {m.questions}
            </p>
            <p>{m.description}</p>
            <p>
              <span className="badge">Phase 2</span>
            </p>
            <Link to={`/module/${m.slug}`}>About this module →</Link>
          </article>
        ))}
      </div>

      <section className="card">
        <h2>How the bands work</h2>
        <p>
          IELTS scores each section from band 0 to 9. Your overall band is
          the average of the four section bands, rounded to the nearest
          whole or half band. Most universities ask for 6.5 overall, often
          with a minimum in each section — which is why PrepSathi always
          reports section bands separately, never just one number.
        </p>
        <p>
          Set a target band when you sign up — for example 6.5 overall
          with 6.0 in Writing — and your dashboard turns it into daily
          practice.
        </p>
      </section>
    </>
  );
}
