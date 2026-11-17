/* Listening audio offline cache (Phase 5.2).

Recordings are cached in Cache Storage under `prepsathi-audio-v1` so a
downloaded part keeps playing offline. Only full 200 responses are
cached — a 206 Range response must never be stored as the whole file,
which is why the service worker also excludes audio paths entirely.

`getAudioUrl` always returns something playable: the cached object URL
on a hit, a fresh object URL after a successful fetch + cache, or the
original URL on any failure so the browser streams it directly.
*/

export const AUDIO_CACHE_NAME = "prepsathi-audio-v1";

/** Resolve an audio_url from the API: relative paths are resolved
 *  against the API base URL; absolute URLs pass through unchanged. */
export function resolveAudioUrl(audioUrl: string, apiBase: string): string {
  if (/^(https?:)?\/\//i.test(audioUrl)) return audioUrl;
  return `${apiBase.replace(/\/$/, "")}${audioUrl}`;
}

export async function getAudioUrl(absoluteUrl: string): Promise<string> {
  if (typeof caches === "undefined") return absoluteUrl;
  try {
    const cache = await caches.open(AUDIO_CACHE_NAME);
    const hit = await cache.match(absoluteUrl);
    if (hit) {
      return URL.createObjectURL(await hit.blob());
    }
    const response = await fetch(absoluteUrl);
    if (!response.ok) return absoluteUrl;
    // Cache only full 200 responses — never a 206 partial.
    if (response.status === 200) {
      await cache.put(absoluteUrl, response.clone());
    }
    return URL.createObjectURL(await response.blob());
  } catch {
    // Any cache/fetch failure: stream the original URL directly.
    return absoluteUrl;
  }
}
