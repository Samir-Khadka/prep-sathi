import { Link } from "react-router-dom";

export default function Privacy() {
  return (
    <section className="card">
      <h1>Privacy note</h1>
      <p>
        PrepSathi is a free practice app. This note explains, in plain
        words, what we store and what we do not.
      </p>

      <h2>What is stored</h2>
      <ul>
        <li>
          <strong>Your account:</strong> your name, email address, and
          your target band. Your password is stored as a one-way hash —
          nobody at PrepSathi can read it.
        </li>
        <li>
          <strong>Your attempts:</strong> your answers and scores from
          timed tests and full mock sittings, so your dashboard can show
          your progress and your band estimates.
        </li>
        <li>
          <strong>Your vocabulary:</strong> the words you have practised
          and your review schedule, so spaced repetition can remind you
          at the right time.
        </li>
      </ul>

      <h2>What is never uploaded</h2>
      <p>
        Speaking practice recordings stay on your device. They are saved
        in your browser on your phone or computer and are never uploaded
        to our servers. You can delete a single recording, or all of them,
        from the Speaking practice page at any time.
      </p>

      <h2>What we do not do</h2>
      <ul>
        <li>No third-party trackers and no advertising.</li>
        <li>We do not sell or share your data with anyone.</li>
        <li>
          We do not use any Cambridge or IELTS test content — all practice
          material is original, written to the official IELTS format.
        </li>
      </ul>

      <h2>Deleting your account</h2>
      <p>
        You can delete your account — including your attempts and
        vocabulary — from your dashboard. Deleting your account removes
        your stored data from our servers. Recordings already live on
        your device only, so deleting them there removes them completely.
      </p>

      <p>
        Questions about this note?{" "}
        <Link to="/">Back to the home page</Link>.
      </p>
    </section>
  );
}
