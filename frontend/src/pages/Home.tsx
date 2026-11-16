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
        <p className="band-label">
          Every band shown on PrepSathi is a practice estimate, not an
          official score.
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      <section aria-labelledby="modules-heading">
        <h2 id="modules-heading">Four modules, one test format</h2>
        <p className="section-intro">
          Practice each section of the test on its own, in the same order
          and timing as the real thing — then put it all together in a
          full mock sitting.
        </p>
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
      </section>

      <section className="card" aria-labelledby="how-heading">
        <h2 id="how-heading">How it works</h2>
        <ol className="steps">
          <li>
            <span className="step-num">1</span>
            <h3>Pick a module</h3>
            <p>
              Start with Listening, Reading, Writing, or Speaking. Each
              one follows the official IELTS format, with original
              practice material written for PrepSathi.
            </p>
          </li>
          <li>
            <span className="step-num">2</span>
            <h3>Practise under time</h3>
            <p>
              Timed tests with the same time limits as the real exam, so
              you learn to finish — not just to answer correctly.
            </p>
          </li>
          <li>
            <span className="step-num">3</span>
            <h3>Sit a full mock</h3>
            <p>
              Listening, Reading, and Writing in one sitting, in test
              order, with no going back to a closed section — just like
              test day. Speaking is practised separately, with on-device
              recording.
            </p>
          </li>
          <li>
            <span className="step-num">4</span>
            <h3>See an honest band estimate</h3>
            <p>
              Every section band and your overall band are shown as a
              practice estimate, not an official score. Your dashboard
              tracks them against the target band you set.
            </p>
          </li>
        </ol>
      </section>

      <section className="card free-strip" aria-labelledby="free-heading">
        <h2 id="free-heading">Free, with no paywall</h2>
        <p>
          Everything on PrepSathi is free: all four modules, every timed
          test, full mock sittings, vocabulary review, and your dashboard.
          There is no premium tier, no locked content, and no ads. You
          only need a free account so your attempts and vocabulary
          progress are saved for you.
        </p>
        <p>
          <Link className="btn" to="/signup">
            Create a free account
          </Link>
        </p>
      </section>

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
        <p className="band-label">
          Reminder: every band on PrepSathi is a practice estimate, not an
          official score. Only an official IELTS test can give you an
          official band.
        </p>
      </section>

      <section className="card">
        <h2>Your data stays yours</h2>
        <p>
          Speaking recordings stay on your device and are never uploaded.
          You can delete your recordings and your account at any time.
          Read the short <Link to="/privacy">privacy note</Link> for
          exactly what is stored and why.
        </p>
      </section>
    </>
  );
}
