import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, type SpeakingSet } from "../api";
import { useAuth } from "../auth";
import { formatTime } from "./practiceShared";

type Phase = "idle" | "prep" | "talk" | "done";

export default function PracticeSpeaking() {
  const { user, loading: authLoading } = useAuth();
  const [sets, setSets] = useState<SpeakingSet[]>([]);
  const [setId, setSetId] = useState("");
  const [error, setError] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [prepLeft, setPrepLeft] = useState(60);
  const [talkLeft, setTalkLeft] = useState(120);
  const [completed, setCompleted] = useState(false);
  const [completing, setCompleting] = useState(false);
  const startedAtRef = useRef<number | null>(null);

  // Recording state
  const [recordingSupported] = useState(
    () =>
      typeof MediaRecorder !== "undefined" &&
      typeof navigator !== "undefined" &&
      !!navigator.mediaDevices?.getUserMedia,
  );
  const [recording, setRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    api
      .speakingSets()
      .then((list) => {
        setSets(list);
        setSetId(list[0]?.id ?? "");
      })
      .catch(() => setError("Could not load the speaking sets."));
  }, []);

  const set = sets.find((s) => s.id === setId);

  // Prep timer
  useEffect(() => {
    if (phase !== "prep") return;
    const timer = window.setInterval(() => {
      setPrepLeft((prev) => {
        if (prev <= 1) {
          window.clearInterval(timer);
          setPhase("talk");
          setTalkLeft(set?.part2.talk_seconds ?? 120);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [phase, set]);

  // Talk timer
  useEffect(() => {
    if (phase !== "talk") return;
    const timer = window.setInterval(() => {
      setTalkLeft((prev) => {
        if (prev <= 1) {
          window.clearInterval(timer);
          setPhase("done");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [phase]);

  // Stop the microphone when leaving the page
  useEffect(
    () => () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  if (authLoading) return <p>Loading…</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Speaking practice</h1>
        <p>Log in to practise speaking and save your attempts.</p>
        <Link className="btn" to="/login">
          Log in
        </Link>
      </section>
    );
  }

  function pickSet(id: string) {
    setSetId(id);
    setPhase("idle");
    setCompleted(false);
    setAudioUrl(null);
    startedAtRef.current = null;
  }

  function startPart2() {
    if (!set) return;
    if (!startedAtRef.current) startedAtRef.current = Date.now();
    setPrepLeft(set.part2.prep_seconds);
    setPhase("prep");
  }

  async function startRecording() {
    if (!recordingSupported) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      streamRef.current = stream;
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        setAudioUrl((old) => {
          if (old) URL.revokeObjectURL(old);
          return URL.createObjectURL(blob);
        });
        stream.getTracks().forEach((t) => t.stop());
      };
      recorder.start();
      setRecording(true);
    } catch {
      setError(
        "Could not access the microphone. Check your browser permission and try again.",
      );
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function markComplete() {
    if (!set || completing) return;
    setCompleting(true);
    const duration = startedAtRef.current
      ? Math.round((Date.now() - startedAtRef.current) / 1000)
      : 0;
    try {
      await api.completeSpeaking(set.id, duration);
      setCompleted(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not save this attempt.",
      );
    } finally {
      setCompleting(false);
    }
  }

  return (
    <>
      <section className="hero">
        <h1>Speaking practice</h1>
        <p className="lead">
          Part 1 questions, a Part 2 cue card with one minute to prepare
          and two minutes to talk, then Part 3 discussion. Your recording
          stays on your device — nothing is uploaded.
        </p>
        <p>
          <label htmlFor="set">Choose a topic</label>
          <select
            id="set"
            value={setId}
            onChange={(e) => pickSet(e.target.value)}
          >
            {sets.map((s) => (
              <option key={s.id} value={s.id}>
                {s.topic}
              </option>
            ))}
          </select>
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      {!set ? (
        <p>Loading…</p>
      ) : (
        <>
          <section className="card">
            <h2>Part 1 — Introduction and interview</h2>
            <p>Answer each question in a few sentences, out loud.</p>
            <ol>
              {set.part1.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ol>
          </section>

          <section className="card">
            <h2>Part 2 — Long turn</h2>
            <div className="cue-card">
              <p>
                <strong>{set.part2.cue}</strong>
              </p>
              <p>You should say:</p>
              <ul>
                {set.part2.points.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
            {phase === "idle" && (
              <p>
                <button onClick={startPart2}>
                  Start 1-minute preparation
                </button>
              </p>
            )}
            {phase === "prep" && (
              <p className="timer">
                Preparation time left:{" "}
                <strong>{formatTime(prepLeft)}</strong> — make notes, then
                talk.
              </p>
            )}
            {(phase === "talk" || phase === "done") && (
              <>
                <p className="timer">
                  Talk time left: <strong>{formatTime(talkLeft)}</strong>
                </p>
                {phase === "talk" && (
                  <p>
                    <button onClick={() => setPhase("done")}>
                      Finish talking
                    </button>
                  </p>
                )}
              </>
            )}
            <h3>Record yourself</h3>
            {!recordingSupported ? (
              <p className="notice">
                This browser does not support recording. You can still
                practise out loud without a recording.
              </p>
            ) : recording ? (
              <p>
                <button className="secondary" onClick={stopRecording}>
                  Stop recording
                </button>{" "}
                Recording… speak for up to two minutes.
              </p>
            ) : (
              <p>
                <button onClick={() => void startRecording()}>
                  {audioUrl ? "Re-record" : "Record my talk"}
                </button>
              </p>
            )}
            {audioUrl && (
              <p>
                <audio controls src={audioUrl} />
              </p>
            )}
            {set.sample_answer && (
              <details>
                <summary>Read a sample talk</summary>
                <p style={{ whiteSpace: "pre-wrap" }}>
                  {set.sample_answer}
                </p>
              </details>
            )}
          </section>

          <section className="card">
            <h2>Part 3 — Two-way discussion</h2>
            <ol>
              {set.part3.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ol>
            {completed ? (
              <p className="notice">
                Saved — this set is recorded as a speaking attempt on your
                dashboard.
              </p>
            ) : (
              <p>
                <button onClick={() => void markComplete()} disabled={completing}>
                  {completing ? "Saving…" : "Mark this set complete"}
                </button>
              </p>
            )}
          </section>
        </>
      )}
    </>
  );
}
