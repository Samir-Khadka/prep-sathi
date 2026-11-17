/* Listening audio player (Phase 5.2).

One player per part. Starting one part pauses any other part on the
page (a module-level "currently playing" element). The file is fetched
through the offline audio cache, so a downloaded part keeps playing
offline. If the file fails to load, the player is replaced by the
audio note — never a broken player — and the transcript (rendered by
the parent, unchanged) is the fallback.
*/
import { useEffect, useRef, useState } from "react";
import { API_URL } from "../api";
import { getAudioUrl, resolveAudioUrl } from "../audioCache";

/** The element currently playing anywhere on the page, if any. */
let activeAudio: HTMLAudioElement | null = null;

export function formatAudioTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

interface ListeningPlayerProps {
  /** Part number, e.g. 1 — shown in the "Now playing" state. */
  part: number;
  /** audio_url from the API: a relative /static/audio/... path or an
   *  absolute URL. Relative paths resolve against the API base URL. */
  audioUrl: string;
  /** Shown instead of the player when the file fails to load. */
  audioNote: string | null;
}

export default function ListeningPlayer({
  part,
  audioUrl,
  audioNote,
}: ListeningPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(false);

  const resolvedUrl = resolveAudioUrl(audioUrl, API_URL);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setError(false);
    setSrc(null);
    setCurrentTime(0);
    setDuration(0);
    setPlaying(false);
    void getAudioUrl(resolvedUrl).then((url) => {
      if (cancelled) {
        if (url !== resolvedUrl) URL.revokeObjectURL(url);
        return;
      }
      if (url !== resolvedUrl) objectUrl = url;
      setSrc(url);
    });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [resolvedUrl]);

  function togglePlay() {
    const audio = audioRef.current;
    if (!audio || error) return;
    if (playing) {
      audio.pause();
      return;
    }
    if (activeAudio && activeAudio !== audio) activeAudio.pause();
    activeAudio = audio;
    void audio.play().catch(() => setError(true));
  }

  if (error) {
    return (
      <p className="notice">
        {audioNote ?? "Audio for this part is not available yet."}
      </p>
    );
  }

  return (
    <div className="listening-player">
      <audio
        ref={audioRef}
        src={src ?? undefined}
        preload="metadata"
        onPlay={() => {
          const audio = audioRef.current;
          if (audio && activeAudio && activeAudio !== audio) {
            activeAudio.pause();
          }
          if (audio) activeAudio = audio;
          setPlaying(true);
        }}
        onPause={() => setPlaying(false)}
        onEnded={() => {
          setPlaying(false);
          if (activeAudio === audioRef.current) activeAudio = null;
        }}
        onTimeUpdate={() => {
          const audio = audioRef.current;
          if (audio) setCurrentTime(audio.currentTime);
        }}
        onLoadedMetadata={() => {
          const audio = audioRef.current;
          if (audio && Number.isFinite(audio.duration)) {
            setDuration(audio.duration);
          }
        }}
        onError={() => setError(true)}
      />
      <button
        type="button"
        onClick={togglePlay}
        disabled={src === null}
        aria-label={playing ? `Pause Part ${part}` : `Play Part ${part}`}
      >
        {playing ? "Pause" : "Play"} Part {part}
      </button>
      <input
        type="range"
        min={0}
        max={duration || 0}
        step={0.1}
        value={currentTime}
        disabled={!duration}
        aria-label={`Seek Part ${part}`}
        onChange={(event) => {
          const value = Number(event.target.value);
          const audio = audioRef.current;
          if (audio) audio.currentTime = value;
          setCurrentTime(value);
        }}
      />
      <span>
        {formatAudioTime(currentTime)} / {formatAudioTime(duration)}
      </span>
      {playing && (
        <p className="now-playing" aria-live="polite">
          Now playing: Part {part}
        </p>
      )}
    </div>
  );
}
