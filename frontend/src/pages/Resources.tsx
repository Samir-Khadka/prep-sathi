import { useEffect, useState } from "react";
import { api, type ResourceLink } from "../api";

export default function Resources() {
  const [links, setLinks] = useState<ResourceLink[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.resources().then(setLinks).catch(() => {
      setError("Could not load the resources list.");
    });
  }, []);

  return (
    <section className="card">
      <h1>Official free material</h1>
      <p>
        These links go to the organisations that run IELTS — the British
        Council, IDP and IELTS.org. PrepSathi links to their free material
        and never copies or re-hosts it.
      </p>
      {error && <p className="error">{error}</p>}
      <ul className="clean">
        {links.map((link) => (
          <li key={link.url}>
            <a href={link.url} target="_blank" rel="noopener noreferrer">
              <strong>{link.title}</strong>
            </a>{" "}
            <span className="badge">{link.provider}</span>
            <p>{link.description}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
