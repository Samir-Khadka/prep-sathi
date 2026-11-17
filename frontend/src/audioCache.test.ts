/* Tests for the Listening audio offline cache (Phase 5.2). */
import { describe, expect, it } from "vitest";
import { getAudioUrl, resolveAudioUrl } from "./audioCache";

describe("resolveAudioUrl", () => {
  it("resolves a relative audio_url against the API base URL", () => {
    expect(
      resolveAudioUrl(
        "/static/audio/listening/L5/part1.mp3",
        "http://localhost:8000",
      ),
    ).toBe("http://localhost:8000/static/audio/listening/L5/part1.mp3");
  });

  it("passes absolute URLs through unchanged", () => {
    expect(
      resolveAudioUrl("https://cdn.example.com/l5p1.mp3", "http://localhost:8000"),
    ).toBe("https://cdn.example.com/l5p1.mp3");
  });

  it("tolerates a trailing slash on the API base URL", () => {
    expect(
      resolveAudioUrl("/static/audio/listening/L1/part2.mp3", "http://localhost:8000/"),
    ).toBe("http://localhost:8000/static/audio/listening/L1/part2.mp3");
  });
});

describe("getAudioUrl", () => {
  it("returns the original URL when Cache Storage is unavailable", async () => {
    // jsdom has no `caches`: the browser must stream directly.
    expect(typeof caches).toBe("undefined");
    const url = "http://localhost:8000/static/audio/listening/L1/part1.mp3";
    await expect(getAudioUrl(url)).resolves.toBe(url);
  });
});
