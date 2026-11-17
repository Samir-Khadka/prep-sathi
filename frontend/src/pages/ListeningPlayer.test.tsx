/* Tests for the Listening player + its wiring in ListeningTest
   (Phase 5.2). jsdom has no Cache Storage and no real audio decoding,
   so getAudioUrl falls back to the original URL and the <audio>
   element's media events are fired by hand. */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, type ListeningTest } from "../api";
import ListeningPlayer, { formatAudioTime } from "./ListeningPlayer";
import ListeningTestPage from "./ListeningTest";

vi.mock("../auth", () => ({
  useAuth: () => ({
    user: { id: 1, email: "learner@prepsathi.example", name: "Test Learner" },
    loading: false,
  }),
}));

const TEST: ListeningTest = {
  id: "L1",
  title: "Listening Test 1",
  parts: [
    {
      part: 1,
      title: "Joining a swimming course",
      setting: "A student phones a leisure centre.",
      transcript: "NARRATOR: You will hear a student phoning a leisure centre.",
      audio_url: null,
      audio_note: "Audio for this part has not been recorded yet.",
      questions: [],
    },
    {
      part: 2,
      title: "A talk on bees",
      setting: "A university lecture about bees.",
      transcript: "LECTURER: Today I want to talk about bees.",
      audio_url: "/static/audio/listening/L1/part2.mp3",
      audio_note: "Audio for this part has not been recorded yet.",
      questions: [],
    },
  ],
};

beforeEach(() => {
  vi.spyOn(api, "listeningTest").mockResolvedValue(TEST);
  vi.spyOn(api, "startListening").mockResolvedValue({
    session_id: "1",
    started_at: new Date().toISOString(),
    time_limit_seconds: null,
    expires_at: null,
  });
});

describe("formatAudioTime", () => {
  it("formats seconds as m:ss", () => {
    expect(formatAudioTime(0)).toBe("0:00");
    expect(formatAudioTime(65)).toBe("1:05");
    expect(formatAudioTime(600)).toBe("10:00");
    expect(formatAudioTime(NaN)).toBe("0:00");
  });
});

describe("ListeningPlayer", () => {
  it("renders with the resolved src when audio_url is set", async () => {
    const { container } = render(
      <ListeningPlayer
        part={2}
        audioUrl="/static/audio/listening/L1/part2.mp3"
        audioNote="Audio for this part has not been recorded yet."
      />,
    );
    const button = await screen.findByLabelText("Play Part 2");
    expect(button).toBeEnabled();
    const audio = container.querySelector("audio");
    expect(audio?.getAttribute("src")).toBe(
      "http://localhost:8000/static/audio/listening/L1/part2.mp3",
    );
    expect(screen.getByText("0:00 / 0:00")).toBeInTheDocument();
  });

  it("shows Now playing and pauses when the audio ends", async () => {
    const { container } = render(
      <ListeningPlayer
        part={2}
        audioUrl="/static/audio/listening/L1/part2.mp3"
        audioNote="Audio for this part has not been recorded yet."
      />,
    );
    await screen.findByLabelText("Play Part 2");
    const audio = container.querySelector("audio") as HTMLAudioElement;
    fireEvent.play(audio);
    expect(screen.getByText("Now playing: Part 2")).toBeInTheDocument();
    fireEvent.ended(audio);
    expect(screen.queryByText("Now playing: Part 2")).not.toBeInTheDocument();
  });

  it("falls back to the audio note when the file fails to load", async () => {
    const { container } = render(
      <ListeningPlayer
        part={2}
        audioUrl="/static/audio/listening/L1/part2.mp3"
        audioNote="Audio for this part has not been recorded yet."
      />,
    );
    await screen.findByLabelText("Play Part 2");
    const audio = container.querySelector("audio") as HTMLAudioElement;
    fireEvent.error(audio);
    await waitFor(() => {
      expect(
        screen.getByText("Audio for this part has not been recorded yet."),
      ).toBeInTheDocument();
    });
    expect(container.querySelector("audio")).not.toBeInTheDocument();
  });
});

describe("ListeningTest wiring", () => {
  function renderPage() {
    return render(
      <MemoryRouter initialEntries={["/listening/L1"]}>
        <Routes>
          <Route path="/listening/:id" element={<ListeningTestPage />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("shows the transcript fallback when audio_url is null", async () => {
    renderPage();
    await screen.findByText("Part 1: Joining a swimming course");
    // No player for Part 1 — just the audio note + transcript.
    expect(screen.queryByLabelText("Play Part 1")).not.toBeInTheDocument();
    expect(
      screen.getByText("Audio for this part has not been recorded yet."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("NARRATOR: You will hear a student phoning a leisure centre."),
    ).toBeInTheDocument();
  });

  it("renders the player with the right src when audio_url is set", async () => {
    const { container } = renderPage();
    const button = await screen.findByLabelText("Play Part 2");
    expect(button).toBeEnabled();
    const audios = container.querySelectorAll("audio");
    expect(audios).toHaveLength(1);
    expect(audios[0].getAttribute("src")).toBe(
      "http://localhost:8000/static/audio/listening/L1/part2.mp3",
    );
    // Transcript <details> stays exactly as-is for the audio part too.
    expect(
      screen.getByText("LECTURER: Today I want to talk about bees."),
    ).toBeInTheDocument();
  });
});
