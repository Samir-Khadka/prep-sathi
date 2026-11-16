import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [targetOverall, setTargetOverall] = useState("6.5");
  const [targetWriting, setTargetWriting] = useState("6.0");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await signup(
        email.trim(),
        password,
        name.trim(),
        targetOverall ? parseFloat(targetOverall) : null,
        targetWriting ? parseFloat(targetWriting) : null,
      );
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-up failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card form">
      <h1>Create a free account</h1>
      <p>
        An account saves your progress when you change phones. Practice
        itself is free — an account never locks it behind a paywall.
      </p>
      <form onSubmit={submit}>
        <label htmlFor="name">Name</label>
        <input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="password">Password (at least 8 characters)</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        <label htmlFor="target-overall">Target overall band</label>
        <input
          id="target-overall"
          type="number"
          min={0}
          max={9}
          step={0.5}
          value={targetOverall}
          onChange={(e) => setTargetOverall(e.target.value)}
        />
        <label htmlFor="target-writing">Target Writing band</label>
        <input
          id="target-writing"
          type="number"
          min={0}
          max={9}
          step={0.5}
          value={targetWriting}
          onChange={(e) => setTargetWriting(e.target.value)}
        />
        <p>
          <button type="submit" disabled={busy}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </p>
        {error && <p className="error">{error}</p>}
      </form>
    </section>
  );
}
