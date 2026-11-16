import { useEffect, useState, type FormEvent } from "react";
import { api, type Feedback, type FeedbackCategory } from "../api";

const CATEGORIES: { value: FeedbackCategory; label: string }[] = [
  { value: "bug", label: "Something is broken" },
  { value: "content", label: "Mistake in the practice material" },
  { value: "feature", label: "Feature request" },
  { value: "other", label: "Something else" },
];

export default function FeedbackPage() {
  const [category, setCategory] = useState<FeedbackCategory>("bug");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mine, setMine] = useState<Feedback[]>([]);

  useEffect(() => {
    api.myFeedback().then(setMine).catch(() => {
      /* past feedback is a nice-to-have; the form still works */
    });
  }, [sent]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.submitFeedback({
        category,
        message: message.trim(),
        page: "feedback",
      });
      setMessage("");
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send feedback");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card form">
      <h1>Send feedback</h1>
      <p>
        Found a mistake, hit a bug, or want something added? Tell us here —
        it goes straight to the PrepSathi team, no email needed.
      </p>
      {sent && (
        <p>
          Thank you — your feedback has been sent. We read every message and
          fix the most-reported issues first.
        </p>
      )}
      <form onSubmit={submit}>
        <label htmlFor="feedback-category">What is it about?</label>
        <select
          id="feedback-category"
          value={category}
          onChange={(e) => setCategory(e.target.value as FeedbackCategory)}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
        <label htmlFor="feedback-message">
          Your message (up to 2000 characters)
        </label>
        <textarea
          id="feedback-message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          maxLength={2000}
          rows={6}
          required
        />
        <p>
          <button type="submit" disabled={busy || message.trim() === ""}>
            {busy ? "Sending…" : "Send feedback"}
          </button>
        </p>
        {error && <p className="error">{error}</p>}
      </form>

      {mine.length > 0 && (
        <>
          <h2>Your past feedback</h2>
          <ul className="clean">
            {mine.map((item) => (
              <li key={item.id}>
                <strong>
                  {CATEGORIES.find((c) => c.value === item.category)?.label ??
                    item.category}
                </strong>{" "}
                <span className="badge">
                  {item.resolved ? "resolved" : "open"}
                </span>
                <p>{item.message}</p>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
