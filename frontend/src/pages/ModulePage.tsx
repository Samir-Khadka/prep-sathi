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

  return (
    <section className="card">
      <p>
        <span className="badge gold">{module.time_minutes}</span>{" "}
        <span className="badge">{module.questions}</span>
      </p>
      <h1>{module.name}</h1>
      <p>{module.description}</p>
      <div className="notice">
        <strong>Coming in Phase 2.</strong> {module.status}
      </div>
      <p>
        Meanwhile, the official free material is the best place to see the
        real format:{" "}
        <Link to="/resources">official resources →</Link>
      </p>
    </section>
  );
}
