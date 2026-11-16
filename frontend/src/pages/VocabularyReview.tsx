import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type VocabularyItem } from "../api";
import { useAuth } from "../auth";

export default function VocabularyReview() {
  const { user, loading: authLoading } = useAuth();
  const [due, setDue] = useState<VocabularyItem[]>([]);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    api
      .vocabularyDue()
      .then(setDue)
      .catch(() => setError("Could not load the words due for review."));
  }, [user]);

  if (authLoading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Vocabulary review</h1>
        <p>Log in to review your words.</p>
        <Link className="btn" to="/login">
          Log in
        </Link>
      </section>
    );
  }

  const current = due[index];

  async function grade(correct: boolean) {
    if (!current || busy) return;
    setBusy(true);
    try {
      await api.reviewWord(current.id, correct);
      setIndex((i) => i + 1);
      setRevealed(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the review.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="hero">
        <h1>Vocabulary review</h1>
        <p className="lead">
          {due.length === 0
            ? "Nothing due right now — well done."
            : `${due.length} word${due.length === 1 ? "" : "s"} due. One card at a time: try to recall the meaning, then check yourself.`}
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      {!current ? (
        <section className="card">
          <h2>All caught up</h2>
          <p>
            No more words due for review. New words become due as their
            review interval passes.
          </p>
          <p>
            <Link className="btn" to="/vocabulary">
              Back to your word list
            </Link>
          </p>
        </section>
      ) : (
        <section className="card">
          <p className="meta">
            Card {index + 1} of {due.length}
          </p>
          <h2>{current.word}</h2>
          <p>
            <span className="badge">{current.topic}</span>
          </p>
          {revealed ? (
            <>
              <p>
                <strong>{current.meaning}</strong>
              </p>
              {current.example && <p className="evidence">{current.example}</p>}
              <p>
                <button
                  onClick={() => void grade(true)}
                  disabled={busy}
                >
                  I knew it
                </button>{" "}
                <button
                  className="secondary"
                  onClick={() => void grade(false)}
                  disabled={busy}
                >
                  Not yet
                </button>
              </p>
            </>
          ) : (
            <p>
              <button onClick={() => setRevealed(true)}>
                Reveal meaning
              </button>
            </p>
          )}
        </section>
      )}
    </>
  );
}
