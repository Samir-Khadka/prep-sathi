import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type ModuleInfo } from "../api";

export default function ModulePage() {
  const { slug } = useParams<{ slug: string }>();
  const [module, setModule] = useState<ModuleInfo | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!slug) return;
    api
      .module(slug)
      .then(setModule)
      .catch(() => setError("Could not load this module."));
  }, [slug]);

  if (error) return <p className="error">{error}</p>;
  if (!module) return <p>Loading…</p>;

  const practiceLinks: Record<string, { to: string; label: string }> = {
    listening: { to: "/practice/listening", label: "Listening practice" },
    reading: { to: "/practice/reading", label: "Reading practice" },
    writing: { to: "/practice/writing", label: "Writing practice" },
    speaking: { to: "/practice/speaking", label: "Speaking practice" },
  };
  const practice = slug ? practiceLinks[slug] : undefined;

  return (
    <section className="card">
      <p>
        <span className="badge gold">{module.time_minutes}</span>{" "}
        <span className="badge">{module.questions}</span>
      </p>
      <h1>{module.name}</h1>
      <p>{module.description}</p>
      {practice && (
        <p>
          <Link className="btn" to={practice.to}>
            Start {practice.label} →
          </Link>
        </p>
      )}
      <p>
        Meanwhile, the official free material is the best place to see the
        real format:{" "}
        <Link to="/resources">official resources →</Link>
      </p>
    </section>
  );
}
