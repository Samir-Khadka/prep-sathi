/* On-device speaking recording history for PrepSathi.
   Audio blobs live in IndexedDB on this device only — nothing is ever
   uploaded, sent to the server, or included in any API call.
   Fluency feedback is an estimated RANGE from timing signals only
   (how long you spoke vs paused), never a precise band score. */

import { BAND_LABEL } from "./api";

export const MAX_SPEAKING_RECORDINGS = 20;
export const SPEAKING_TARGET_SECONDS = 120;

const DB_NAME = "prepsathi-speaking-history";
const DB_VERSION = 1;
const STORE_NAME = "recordings";

/** RMS volume below this counts as silence. */
const SILENCE_THRESHOLD = 0.02;
/** A silence run longer than this counts as a pause. */
const PAUSE_MIN_SECONDS = 0.7;
/** The analyser is sampled this often while recording (~10x/second). */
const SAMPLE_INTERVAL_SECONDS = 0.1;

export interface FluencyEstimate {
  durationSeconds: number;
  speechSeconds: number;
  pauseCount: number;
  longestPauseSeconds: number;
  bandLow: number;
  bandHigh: number;
  bandLabel: string;
  notes: string[];
}

export interface SpeakingRecordingMeta {
  id: string;
  setId: string;
  topic: string;
  part: string;
  durationSeconds: number;
  createdAt: number;
  fluency: FluencyEstimate | null;
}

export interface SpeakingRecording extends SpeakingRecordingMeta {
  blob: Blob;
  mimeType: string;
}

/* ------------------------------------------------------------------ */
/* Fluency math — pure functions, no browser APIs, unit-testable.      */
/* ------------------------------------------------------------------ */

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

type BandRange = [number, number];

const BAND_STEPS: BandRange[] = [
  [4.0, 5.0],
  [4.5, 5.5],
  [5.0, 6.0],
  [6.0, 7.0],
  [6.5, 7.5],
];

function stepDown(range: BandRange): BandRange {
  const idx = BAND_STEPS.findIndex(
    ([lo, hi]) => lo === range[0] && hi === range[1],
  );
  if (idx <= 0) return BAND_STEPS[0];
  return BAND_STEPS[idx - 1];
}

/**
 * Estimated band RANGE from timing signals only.
 * Coverage = speech time vs the target talk time. Frequent long pauses
 * pull the range down: severe hesitation caps it at 4.5–5.5 even when
 * coverage was good; moderate hesitation drops it one step.
 */
export function estimateBandRange(
  speechSeconds: number,
  targetSeconds: number,
  pauseCount: number,
  longestPauseSeconds: number,
): { bandLow: number; bandHigh: number } {
  const coverage =
    targetSeconds > 0 ? speechSeconds / targetSeconds : 0;
  let range: BandRange;
  if (coverage >= 0.8) range = [6.5, 7.5];
  else if (coverage >= 0.65) range = [6.0, 7.0];
  else if (coverage >= 0.45) range = [5.0, 6.0];
  else if (coverage >= 0.25) range = [4.5, 5.5];
  else range = [4.0, 5.0];

  const severeHesitation = pauseCount >= 10 || longestPauseSeconds >= 6;
  const moderateHesitation =
    !severeHesitation && (pauseCount > 6 || longestPauseSeconds > 3);
  if (severeHesitation) {
    range = coverage >= 0.25 ? [4.5, 5.5] : [4.0, 5.0];
  } else if (moderateHesitation) {
    range = stepDown(range);
  }
  return { bandLow: range[0], bandHigh: range[1] };
}

function buildFluencyNotes(
  durationSeconds: number,
  speechSeconds: number,
  targetSeconds: number,
  pauseCount: number,
  longestPauseSeconds: number,
): string[] {
  const notes: string[] = [];
  const coverage =
    targetSeconds > 0 ? speechSeconds / targetSeconds : 0;
  notes.push(
    `You spoke for ${speechSeconds} of ${targetSeconds} seconds ` +
      `(recording ${durationSeconds}s) with ${pauseCount} ` +
      `pause${pauseCount === 1 ? "" : "s"} over 0.7s` +
      (longestPauseSeconds > 0
        ? `; longest pause ${longestPauseSeconds}s.`
        : "."),
  );
  if (coverage >= 0.8 && pauseCount <= 3) {
    notes.push(
      "You kept talking through most of the two minutes with very few pauses.",
    );
  }
  if (longestPauseSeconds >= 5) {
    notes.push(
      `Your longest pause was ${longestPauseSeconds}s — long pauses break ` +
        "fluency; try bridging with a short phrase while you think of what to say next.",
    );
  }
  if (coverage < 0.45) {
    notes.push(
      "You stopped well short of the two-minute target — aim to keep talking until the timer ends.",
    );
  }
  notes.push(
    "This range comes from timing signals only — it cannot judge pronunciation, vocabulary, or ideas.",
  );
  return notes;
}

/**
 * Turn a series of RMS volume samples into a fluency estimate.
 * `levels` are sampled every `sampleIntervalSeconds`; a pause is a
 * below-threshold run longer than 0.7s.
 */
export function analyseFluency(
  levels: number[],
  sampleIntervalSeconds: number,
  durationSeconds: number,
  targetSeconds: number,
): FluencyEstimate {
  let speechSamples = 0;
  let pauseCount = 0;
  let longestPauseSeconds = 0;
  let silentRun = 0;

  const closeRun = () => {
    const runSeconds = silentRun * sampleIntervalSeconds;
    if (runSeconds > PAUSE_MIN_SECONDS) {
      pauseCount += 1;
      longestPauseSeconds = Math.max(longestPauseSeconds, runSeconds);
    }
    silentRun = 0;
  };

  for (const level of levels) {
    if (level >= SILENCE_THRESHOLD) {
      speechSamples += 1;
      closeRun();
    } else {
      silentRun += 1;
    }
  }
  closeRun();

  const speechSeconds = Math.min(
    durationSeconds,
    round1(speechSamples * sampleIntervalSeconds),
  );
  longestPauseSeconds = round1(longestPauseSeconds);
  const { bandLow, bandHigh } = estimateBandRange(
    speechSeconds,
    targetSeconds,
    pauseCount,
    longestPauseSeconds,
  );
  return {
    durationSeconds,
    speechSeconds,
    pauseCount,
    longestPauseSeconds,
    bandLow,
    bandHigh,
    bandLabel: BAND_LABEL,
    notes: buildFluencyNotes(
      durationSeconds,
      speechSeconds,
      targetSeconds,
      pauseCount,
      longestPauseSeconds,
    ),
  };
}

/* ------------------------------------------------------------------ */
/* Live fluency tracking during a recording (AnalyserNode).            */
/* ------------------------------------------------------------------ */

export interface FluencyTracker {
  stop: () => FluencyEstimate;
}

/**
 * Sample the mic stream's volume ~10x/second while recording.
 * Returns null when the Web Audio API is unavailable — the caller
 * should then record without a fluency estimate.
 */
export function createFluencyTracker(
  stream: MediaStream,
  targetSeconds: number = SPEAKING_TARGET_SECONDS,
): FluencyTracker | null {
  try {
    const AudioCtx =
      window.AudioContext ??
      (
        window as unknown as {
          webkitAudioContext?: typeof AudioContext;
        }
      ).webkitAudioContext;
    if (!AudioCtx) return null;
    const ctx = new AudioCtx();
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    const data = new Uint8Array(analyser.fftSize);
    const levels: number[] = [];
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128;
        sum += v * v;
      }
      levels.push(Math.sqrt(sum / data.length));
    }, SAMPLE_INTERVAL_SECONDS * 1000);
    return {
      stop() {
        window.clearInterval(timer);
        const durationSeconds = Math.max(
          1,
          Math.round((Date.now() - startedAt) / 1000),
        );
        void ctx.close().catch(() => undefined);
        return analyseFluency(
          levels,
          SAMPLE_INTERVAL_SECONDS,
          durationSeconds,
          targetSeconds,
        );
      },
    };
  } catch {
    return null;
  }
}

/* ------------------------------------------------------------------ */
/* IndexedDB storage — blobs persist across reloads, on this device.   */
/* ------------------------------------------------------------------ */

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("This browser does not support on-device storage."));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () =>
      reject(req.error ?? new Error("Could not open on-device storage."));
  });
}

function requestToPromise<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () =>
      reject(req.error ?? new Error("On-device storage failed."));
  });
}

function txDone(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () =>
      reject(tx.error ?? new Error("On-device storage failed."));
    tx.onabort = () =>
      reject(tx.error ?? new Error("On-device storage failed."));
  });
}

/** Drop the oldest recordings once the 20-recording cap is exceeded. */
async function pruneOldest(db: IDBDatabase): Promise<void> {
  const tx = db.transaction(STORE_NAME, "readwrite");
  const store = tx.objectStore(STORE_NAME);
  const all = (await requestToPromise(
    store.getAll(),
  )) as SpeakingRecording[];
  const sorted = all.sort((a, b) => a.createdAt - b.createdAt);
  const excess = sorted.length - MAX_SPEAKING_RECORDINGS;
  for (let i = 0; i < excess; i++) {
    revokeSpeakingPlaybackUrl(sorted[i].id);
    store.delete(sorted[i].id);
  }
  await txDone(tx);
}

export async function saveSpeakingRecording(input: {
  setId: string;
  topic: string;
  part: string;
  durationSeconds: number;
  blob: Blob;
  mimeType: string;
  fluency: FluencyEstimate | null;
}): Promise<string> {
  const db = await openDb();
  try {
    const record: SpeakingRecording = {
      id: crypto.randomUUID(),
      createdAt: Date.now(),
      ...input,
    };
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(record);
    await txDone(tx);
    await pruneOldest(db);
    return record.id;
  } finally {
    db.close();
  }
}

/** Newest first. Blobs are NOT loaded here — use getSpeakingRecordingBlob. */
export async function listSpeakingRecordings(): Promise<
  SpeakingRecordingMeta[]
> {
  const db = await openDb();
  try {
    const tx = db.transaction(STORE_NAME, "readonly");
    const all = (await requestToPromise(
      tx.objectStore(STORE_NAME).getAll(),
    )) as SpeakingRecording[];
    return all
      .sort((a, b) => b.createdAt - a.createdAt)
      .map(
        ({
          blob: _blob,
          mimeType: _mimeType,
          ...meta
        }): SpeakingRecordingMeta => meta,
      );
  } finally {
    db.close();
  }
}

export async function getSpeakingRecordingBlob(
  id: string,
): Promise<Blob | null> {
  const db = await openDb();
  try {
    const tx = db.transaction(STORE_NAME, "readonly");
    const record = (await requestToPromise(
      tx.objectStore(STORE_NAME).get(id),
    )) as SpeakingRecording | undefined;
    return record?.blob ?? null;
  } finally {
    db.close();
  }
}

export async function deleteSpeakingRecording(id: string): Promise<void> {
  revokeSpeakingPlaybackUrl(id);
  const db = await openDb();
  try {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(id);
    await txDone(tx);
  } finally {
    db.close();
  }
}

export async function clearSpeakingRecordings(): Promise<void> {
  revokeAllSpeakingPlaybackUrls();
  const db = await openDb();
  try {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).clear();
    await txDone(tx);
  } finally {
    db.close();
  }
}

/* ------------------------------------------------------------------ */
/* Playback URLs — tracked so deletes/clears can revoke them.          */
/* ------------------------------------------------------------------ */

const liveUrls = new Map<string, string>();

export function createSpeakingPlaybackUrl(
  id: string,
  blob: Blob,
): string {
  revokeSpeakingPlaybackUrl(id);
  const url = URL.createObjectURL(blob);
  liveUrls.set(id, url);
  return url;
}

export function revokeSpeakingPlaybackUrl(id: string): void {
  const url = liveUrls.get(id);
  if (url) {
    URL.revokeObjectURL(url);
    liveUrls.delete(id);
  }
}

export function revokeAllSpeakingPlaybackUrls(): void {
  for (const url of liveUrls.values()) URL.revokeObjectURL(url);
  liveUrls.clear();
}
