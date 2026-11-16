import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, BAND_LABEL, type SpeakingSet } from "../api";
import { useAuth } from "../auth";
import { BandLabel, formatTime } from "./practiceShared";
import {
  clearSpeakingRecordings,
  createFluencyTracker,
  createSpeakingPlaybackUrl,
  deleteSpeakingRecording,
  getSpeakingRecordingBlob,
  listSpeakingRecordings,
  MAX_SPEAKING_RECORDINGS,
  revokeAllSpeakingPlaybackUrls,
  revokeSpeakingPlaybackUrl,
  saveSpeakingRecording,
  SPEAKING_TARGET_SECONDS,
  type FluencyEstimate,
  type FluencyTracker,
  type SpeakingRecordingMeta,
} from "../speakingHistory";

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
  const fluencyTrackerRef = useRef<FluencyTracker | null>(null);
  const recordingStartedAtRef = useRef<number | null>(null);

  // The finished recording waiting to be saved, if the learner chooses.
  const [lastRecording, setLastRecording] = useState<{
    blob: Blob;
    mimeType: string;
    durationSeconds: number;
    fluency: FluencyEstimate | null;
  } | null>(null);
  const [savedToHistory, setSavedToHistory] = useState(false);
  const [savingRecording, setSavingRecording] = useState(false);

  // On-device history (IndexedDB — recordings never leave this device).
  const [history, setHistory] = useState<SpeakingRecordingMeta[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [playbackUrls, setPlaybackUrls] = useState<Record<string, string>>(
    {},
  );

  async function refreshHistory() {
    try {
      setHistory(await listSpeakingRecordings());
    } catch {
      setError("Could not load your saved recordings.");
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    void refreshHistory();
  }, []);

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
      revokeAllSpeakingPlaybackUrls();
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
    setLastRecording(null);
    setSavedToHistory(false);
    setPlaybackUrls({});
    revokeAllSpeakingPlaybackUrls();
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
      recordingStartedAtRef.current = Date.now();
      // Fluency is measured live from the mic volume; if the Web Audio
      // API is unavailable the recording still works, just without an
      // estimate.
      fluencyTrackerRef.current = createFluencyTracker(
        stream,
        set?.part2.talk_seconds ?? SPEAKING_TARGET_SECONDS,
      );
      const recorder = new MediaRecorder(stream);
      recorderRef.current = recorder;
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        const durationSeconds = recordingStartedAtRef.current
          ? Math.max(
              1,
              Math.round(
                (Date.now() - recordingStartedAtRef.current) / 1000,
              ),
            )
          : 0;
        const fluency = fluencyTrackerRef.current?.stop() ?? null;
        fluencyTrackerRef.current = null;
        setLastRecording({
          blob,
          mimeType: blob.type || "audio/webm",
          durationSeconds,
          fluency,
        });
        setSavedToHistory(false);
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

  /** Saving is explicit — a recording is only stored when the learner asks. */
  async function saveRecording() {
    if (!set || !lastRecording || savingRecording) return;
    setSavingRecording(true);
    try {
      await saveSpeakingRecording({
        setId: set.id,
        topic: set.topic,
        part: "Part 2",
        durationSeconds: lastRecording.durationSeconds,
        blob: lastRecording.blob,
        mimeType: lastRecording.mimeType,
        fluency: lastRecording.fluency,
      });
      setSavedToHistory(true);
      await refreshHistory();
    } catch {
      setError(
        "Could not save this recording on your device. Your browser may be blocking on-device storage.",
      );
    } finally {
      setSavingRecording(false);
    }
  }

  async function playRecording(id: string) {
    if (playbackUrls[id]) return;
    try {
      const blob = await getSpeakingRecordingBlob(id);
      if (!blob) {
        setError("That recording could not be found on this device.");
        return;
      }
      const url = createSpeakingPlaybackUrl(id, blob);
      setPlaybackUrls((prev) => ({ ...prev, [id]: url }));
    } catch {
      setError("Could not play that recording.");
    }
  }

  function hidePlayback(id: string) {
    revokeSpeakingPlaybackUrl(id);
    setPlaybackUrls((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  async function deleteRecording(id: string) {
    hidePlayback(id);
    try {
      await deleteSpeakingRecording(id);
      await refreshHistory();
    } catch {
      setError("Could not delete that recording.");
    }
  }

  async function clearAllRecordings() {
    if (
      !window.confirm(
        "Delete all your saved speaking recordings from this device?",
      )
    ) {
      return;
    }
    setPlaybackUrls({});
    try {
      await clearSpeakingRecordings();
      await refreshHistory();
    } catch {
      setError("Could not delete your recordings.");
    }
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
            {lastRecording && (
              <div>
                {lastRecording.fluency ? (
                  <>
                    <p>
                      <strong>
                        Band {lastRecording.fluency.bandLow.toFixed(1)}–
                        {lastRecording.fluency.bandHigh.toFixed(1)}
                      </strong>{" "}
                      <BandLabel />
                    </p>
                    <ul className="clean">
                      {lastRecording.fluency.notes.map((note, i) => (
                        <li key={i}>{note}</li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p className="notice">
                    No fluency estimate for this recording — your browser
                    could not measure the microphone volume while
                    recording.
                  </p>
                )}
                {savedToHistory ? (
                  <p className="notice">
                    Saved to your recordings below — it stays on this
                    device and is never uploaded.
                  </p>
                ) : (
                  <p>
                    <button
                      onClick={() => void saveRecording()}
                      disabled={savingRecording}
                    >
                      {savingRecording
                        ? "Saving…"
                        : "Save this recording to my history"}
                    </button>
                  </p>
                )}
              </div>
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

          <section className="card">
            <h2>My recordings</h2>
            <p>
              Recordings are stored only on this device — they are never
              uploaded or sent anywhere. Only your{" "}
              {MAX_SPEAKING_RECORDINGS} most recent recordings are kept;
              older ones are removed automatically.
            </p>
            <p className="notice">
              Any band range shown here is guidance from timing signals
              only — it cannot judge pronunciation, vocabulary, or ideas.
              ({BAND_LABEL})
            </p>
            {historyLoading ? (
              <p>Loading…</p>
            ) : history.length === 0 ? (
              <p>
                No recordings saved yet. Record a Part 2 talk above and
                choose “Save this recording to my history” to keep it here
                so you can listen back later.
              </p>
            ) : (
              <>
                <p>
                  <button
                    className="secondary"
                    onClick={() => void clearAllRecordings()}
                  >
                    Delete all
                  </button>
                </p>
                <ul className="clean">
                  {history.map((rec) => (
                    <li key={rec.id}>
                      <p>
                        <strong>{rec.topic}</strong> — {rec.part}
                      </p>
                      <p>
                        {new Date(rec.createdAt).toLocaleDateString(
                          undefined,
                          {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          },
                        )}{" "}
                        {new Date(rec.createdAt).toLocaleTimeString(
                          undefined,
                          { hour: "2-digit", minute: "2-digit" },
                        )}{" "}
                        · {formatTime(rec.durationSeconds)}
                        {rec.fluency
                          ? ` · Band ${rec.fluency.bandLow.toFixed(1)}–${rec.fluency.bandHigh.toFixed(1)} (${rec.fluency.bandLabel})`
                          : " · no fluency estimate"}
                      </p>
                      {rec.fluency && (
                        <p>{rec.fluency.notes[0]}</p>
                      )}
                      <p>
                        {playbackUrls[rec.id] ? (
                          <>
                            <audio controls src={playbackUrls[rec.id]} />{" "}
                            <button
                              className="secondary"
                              onClick={() => hidePlayback(rec.id)}
                            >
                              Hide player
                            </button>
                          </>
                        ) : (
                          <button
                            className="secondary"
                            onClick={() => void playRecording(rec.id)}
                          >
                            Play
                          </button>
                        )}{" "}
                        <button
                          className="secondary"
                          onClick={() => void deleteRecording(rec.id)}
                        >
                          Delete
                        </button>
                      </p>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        </>
      )}
    </>
  );
}
