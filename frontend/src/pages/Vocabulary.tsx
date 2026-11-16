import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type VocabularyItem } from "../api";
import { useAuth } from "../auth";

export default function Vocabulary() {
  const { user, loading } = useAuth();
  const [words, setWords] = useState<VocabularyItem[]>([]);
  const [word, setWord] = useState("");
  const [meaning, setMeaning] = useState("");
  const [topic, setTopic] = useState("general");
  const [error, setError] = useState("");
  const [seedMsg, setSeedMsg] = useState("");
  const [seeding, setSeeding] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.vocabulary().then(setWords).catch(() => {
      setError("Could not load your vocabulary.");
    });
  }, [user]);

  if (loading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Vocabulary</h1>
        <p>Log in to keep your word list.</p>
        <Link className="btn" to="/login">
          Log in
        </Link>
      </section>
    );
  }

  async function add(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const item = await api.addWord({
        word: word.trim(),
        meaning: meaning.trim(),
        topic: topic.trim() || "general",
      });
      setWords([item, ...words]);
      setWord("");
      setMeaning("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add the word");
    }
  }

  async function seed() {
    setSeeding(true);
    setSeedMsg("");
    try {
      const res = await api.seedVocabulary();
      setSeedMsg(
        `Added ${res.added} words from the starter deck (${res.skipped} already in your list).`,
      );
      setWords(await api.vocabulary());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the starter deck.");
    } finally {
      setSeeding(false);
    }
  }

  async function remove(id: number) {
    await api.deleteWord(id);
    setWords(words.filter((w) => w.id !== id));
  }

  return (
    <>
      <section className="card form">
        <h1>Vocabulary</h1>
        <p>
          Words harvested from your own reading and listening mistakes —
          reviewed with spaced repetition. Load the 200-word starter deck
          to begin, or add your own words below.
        </p>
        <p>
          <button type="button" onClick={() => void seed()} disabled={seeding}>
            {seeding ? "Loading…" : "Load starter deck"}
          </button>{" "}
          <Link className="btn secondary" to="/vocabulary/review">
            Review due words
          </Link>
        </p>
        {seedMsg && <p className="notice">{seedMsg}</p>}
        <form onSubmit={add}>
          <label htmlFor="word">Word</label>
          <input
            id="word"
            value={word}
            onChange={(e) => setWord(e.target.value)}
            required
          />
          <label htmlFor="meaning">Meaning</label>
          <input
            id="meaning"
            value={meaning}
            onChange={(e) => setMeaning(e.target.value)}
          />
          <label htmlFor="topic">Topic</label>
          <input
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
          <p>
            <button type="submit">Add word</button>
          </p>
          {error && <p className="error">{error}</p>}
        </form>
      </section>

      <section className="card">
        <h2>Your words ({words.length})</h2>
        {words.length === 0 ? (
          <p>No words yet — add your first one above.</p>
        ) : (
          <ul className="clean">
            {words.map((w) => (
              <li key={w.id}>
                <strong>{w.word}</strong> — {w.meaning}{" "}
                <span className="badge">{w.topic}</span>{" "}
                <button
                  className="secondary"
                  onClick={() => void remove(w.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
