import { useEffect, useState } from "react";
import { HashRouter, Link, Route, Routes, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import Login from "./pages/Login";
import ModulePage from "./pages/ModulePage";
import Resources from "./pages/Resources";
import Signup from "./pages/Signup";
import Vocabulary from "./pages/Vocabulary";
import "./styles.css";

function Nav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <nav className="main">
      <Link to="/">Practice</Link>
      <Link to="/resources">Official resources</Link>
      {user ? (
        <>
          <Link to="/dashboard">Dashboard</Link>
          <Link to="/vocabulary">Vocabulary</Link>
          <button
            className="secondary"
            onClick={() => {
              logout();
              navigate("/");
            }}
          >
            Log out ({user.name || user.email})
          </button>
        </>
      ) : (
        <>
          <Link to="/login">Log in</Link>
          <Link to="/signup">Sign up</Link>
        </>
      )}
    </nav>
  );
}

function InstallButton() {
  const [prompt, setPrompt] = useState<Event & {
    prompt: () => void;
  } | null>(null);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setPrompt(e as Event & { prompt: () => void });
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  if (!prompt) return null;
  return (
    <button className="secondary" onClick={() => prompt.prompt()}>
      Install PrepSathi on your phone
    </button>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <header className="site">
          <div className="bar">
            <Link className="brand" to="/">
              PrepSathi<small>IELTS-format practice</small>
            </Link>
            <Nav />
          </div>
        </header>
        <main className="container">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/vocabulary" element={<Vocabulary />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="/module/:slug" element={<ModulePage />} />
          </Routes>
          <p className="honesty">
            Every band shown on PrepSathi is a practice estimate, not an
            official score. All practice material is original, written to
            the official IELTS format — no Cambridge test content is used.
          </p>
        </main>
        <footer className="site">
          <InstallButton />
          <p>
            PrepSathi — free IELTS-format practice for Nepali phone-first
            learners.
          </p>
        </footer>
      </HashRouter>
    </AuthProvider>
  );
}
