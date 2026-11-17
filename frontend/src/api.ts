/* PrepSathi API client. The token lives in localStorage; nothing
   sensitive is ever written into the code itself. */

export const API_URL =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface User {
  id: number;
  email: string;
  name: string;
  target_band_overall: number | null;
  target_band_writing: number | null;
  created_at: string;
}

export interface ModuleInfo {
  slug: string;
  name: string;
  time_minutes: string;
  questions: string;
  description: string;
  status: string;
}

export interface ResourceLink {
  title: string;
  url: string;
  description: string;
  provider: string;
}

export interface Dashboard {
  attempts_total: number;
  attempts_by_module: Record<string, number>;
  vocabulary_total: number;
  vocabulary_due: number;
  target_band_overall: number | null;
  target_band_writing: number | null;
  latest_band_by_module?: Record<string, number | null>;
  overall_estimate?: number | null;
  attempts_recent?: AttemptSummary[];
}

export interface AttemptSummary {
  id: number;
  module: string;
  kind: string;
  score_raw: number | null;
  band_estimate: number | null;
  duration_seconds: number | null;
  created_at: string;
}

export type TestMode = "timed" | "practice";

export interface TestPartSummary {
  part: number;
  title: string;
  question_count: number;
  has_audio: boolean;
}

export interface ListeningTestSummary {
  id: string;
  title: string;
  parts: TestPartSummary[];
  total_questions: number;
  time_limit_seconds: number;
}

export interface PracticeQuestion {
  no: number;
  type: "short" | "mcq" | "tfng";
  prompt: string;
  options?: string[];
}

export interface ListeningPart {
  part: number;
  title: string;
  setting: string;
  transcript: string;
  audio_url: string | null;
  audio_note: string | null;
  questions: PracticeQuestion[];
}

export interface ListeningTest {
  id: string;
  title: string;
  parts: ListeningPart[];
}

export interface ReadingPassageSummary {
  section: number;
  title: string;
  question_count: number;
}

export interface ReadingTestSummary {
  id: string;
  track: "academic" | "general";
  title: string;
  passages?: ReadingPassageSummary[];
  total_questions: number;
  time_limit_seconds: number;
}

export interface ReadingPassage {
  section: number;
  title: string;
  text: string;
  questions: PracticeQuestion[];
}

export interface ReadingTest {
  id: string;
  track: "academic" | "general";
  title: string;
  passages: ReadingPassage[];
}

export interface TestSession {
  session_id: string;
  started_at: string;
  time_limit_seconds: number | null;
  expires_at: string | null;
}

export interface QuestionResult {
  no: number;
  correct: boolean;
  your_answer: string | number | null;
  correct_answer: string | number | null;
  explanation: string;
  evidence: string;
}

export interface SubmitResult {
  score_raw: number;
  band_estimate: number;
  band_label: string;
  duration_seconds: number;
  overtime: boolean;
  results: QuestionResult[];
}

export interface WritingPromptSummary {
  id: string;
  track: "academic" | "general";
  task: 1 | 2;
  title: string;
  prompt: string;
  min_words: number;
  suggested_minutes: number;
}

export interface WritingPrompt extends WritingPromptSummary {
  model_answer: string;
  commentary: string;
}

export interface WritingSubmitResult {
  word_count: number;
  min_words: number;
  meets_minimum: boolean;
  attempt_id: number;
}

export interface SpeakingSet {
  id: string;
  topic: string;
  part1: string[];
  part2: {
    cue: string;
    points: string[];
    prep_seconds: number;
    talk_seconds: number;
  };
  part3: string[];
  sample_answer?: string | null;
}

export const BAND_LABEL = "practice estimate, not an official score";

export interface VocabularyItem {
  id: number;
  word: string;
  meaning: string;
  topic: string;
  example?: string | null;
  interval_days: number;
  next_review: string;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/* In-app feedback loop (Phase 4): learners send feedback in-app;    */
/* admins triage it in-app. No third-party service, no email.        */
/* ------------------------------------------------------------------ */

export type FeedbackCategory = "bug" | "content" | "feature" | "other";

export interface Feedback {
  id: number;
  user_id: number;
  category: FeedbackCategory;
  message: string;
  page: string | null;
  resolved: boolean;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/* Full mocks (Phase 3): Listening → Reading → Writing → Speaking,    */
/* in one sitting, in test order, no going back. Every band is a      */
/* practice estimate, never an official score.                        */
/* ------------------------------------------------------------------ */

export type MockTrack = "academic" | "general";

export type MockSectionKey =
  | "listening"
  | "reading"
  | "writing"
  | "speaking"
  | "done";

export interface MockStartResponse {
  mock_id: number;
  track: string;
  current_section: string;
  listening_test_id: string;
  reading_test_id: string;
  writing_task1_prompt_id: string;
  writing_task2_prompt_id: string;
  started_at: string;
  section_expires_at: string | null;
  band_label: string;
}

export interface MockSummary {
  mock_id: number;
  track: string;
  status: string;
  current_section: string;
  overall_band: number | null;
  started_at: string;
}

export interface MockScoredSection {
  status: string;
  score_raw: number | null;
  band_estimate: number | null;
}

export interface MockWritingSection {
  status: string;
  band_low: number | null;
  band_high: number | null;
}

export interface MockSpeakingSection {
  status: string;
  band_estimate: number | null;
}

export interface MockSections {
  listening: MockScoredSection;
  reading: MockScoredSection;
  writing: MockWritingSection;
  speaking: MockSpeakingSection;
}

export interface MockDetail {
  mock_id: number;
  track: string;
  status: string;
  current_section: string;
  started_at: string;
  section_expires_at: string | null;
  sections: MockSections;
  overall_band: number | null;
  band_label: string;
}

export interface MockSubmitResult extends SubmitResult {
  next_section: string;
  section_expires_at: string | null;
}

export interface WritingFeedbackCriterion {
  band_low: number;
  band_high: number;
  notes: string[];
}

export interface WritingFeedback {
  prompt_id: string;
  word_count: number;
  min_words: number;
  meets_minimum: boolean;
  band_low: number;
  band_high: number;
  band_label: string;
  criteria: Record<string, WritingFeedbackCriterion>;
  limits: string;
}

export interface MockWritingTaskResult {
  word_count: number;
  min_words: number;
  meets_minimum: boolean;
  feedback: WritingFeedback;
}

export interface MockWritingSubmitResult {
  task1: MockWritingTaskResult;
  task2: MockWritingTaskResult;
  writing_band_low: number;
  writing_band_high: number;
  next_section: string;
}

export interface MockSpeakingCompleteResult {
  overall_band: number | null;
  band_label: string;
  status: string;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("prepsathi_token");
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body: unknown = await res.json();
      if (body && typeof body === "object" && "detail" in body) {
        detail = String((body as { detail: unknown }).detail);
      }
    } catch {
      /* keep the status text */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  signup: (payload: {
    email: string;
    password: string;
    name: string;
    target_band_overall?: number | null;
    target_band_writing?: number | null;
  }) =>
    request<{ access_token: string }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/auth/me"),
  modules: () => request<ModuleInfo[]>("/api/modules"),
  module: (slug: string) => request<ModuleInfo>(`/api/modules/${slug}`),
  resources: () => request<ResourceLink[]>("/api/resources"),
  dashboard: () => request<Dashboard>("/api/dashboard"),
  vocabulary: () => request<VocabularyItem[]>("/api/vocabulary"),
  addWord: (payload: { word: string; meaning: string; topic: string }) =>
    request<VocabularyItem>("/api/vocabulary", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteWord: (id: number) =>
    request<void>(`/api/vocabulary/${id}`, { method: "DELETE" }),
  vocabularyDue: () => request<VocabularyItem[]>("/api/vocabulary/due"),
  reviewWord: (id: number, correct: boolean) =>
    request<VocabularyItem>(`/api/vocabulary/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ correct }),
    }),
  seedVocabulary: () =>
    request<{ added: number; skipped: number }>("/api/vocabulary/seed", {
      method: "POST",
    }),
  listeningTests: () =>
    request<ListeningTestSummary[]>("/api/practice/listening"),
  listeningTest: (id: string) =>
    request<ListeningTest>(`/api/practice/listening/${id}`),
  startListening: (id: string, mode: TestMode) =>
    request<TestSession>(`/api/practice/listening/${id}/start`, {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  submitListening: (
    id: string,
    sessionId: string,
    answers: Record<string, string | number>,
  ) =>
    request<SubmitResult>(`/api/practice/listening/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, answers }),
    }),
  readingTests: (track?: "academic" | "general") =>
    request<ReadingTestSummary[]>(
      track ? `/api/practice/reading?track=${track}` : "/api/practice/reading",
    ),
  readingTest: (id: string) => request<ReadingTest>(`/api/practice/reading/${id}`),
  startReading: (id: string, mode: TestMode) =>
    request<TestSession>(`/api/practice/reading/${id}/start`, {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  submitReading: (
    id: string,
    sessionId: string,
    answers: Record<string, string | number>,
  ) =>
    request<SubmitResult>(`/api/practice/reading/${id}/submit`, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, answers }),
    }),
  writingPrompts: (track?: "academic" | "general") =>
    request<WritingPromptSummary[]>(
      track ? `/api/practice/writing?track=${track}` : "/api/practice/writing",
    ),
  writingPrompt: (id: string) =>
    request<WritingPrompt>(`/api/practice/writing/${id}`),
  submitWriting: (promptId: string, text: string, durationSeconds: number) =>
    request<WritingSubmitResult>("/api/practice/writing/submit", {
      method: "POST",
      body: JSON.stringify({
        prompt_id: promptId,
        text,
        duration_seconds: durationSeconds,
      }),
    }),
  speakingSets: () => request<SpeakingSet[]>("/api/practice/speaking"),
  completeSpeaking: (setId: string, durationSeconds: number) =>
    request<{ attempt_id: number }>("/api/practice/speaking/complete", {
      method: "POST",
      body: JSON.stringify({ set_id: setId, duration_seconds: durationSeconds }),
    }),
  /* Full mocks (Phase 3) */
  startMock: (track: MockTrack) =>
    request<MockStartResponse>("/api/mock/start", {
      method: "POST",
      body: JSON.stringify({ track }),
    }),
  listMocks: () => request<MockSummary[]>("/api/mock"),
  getMock: (mockId: number) => request<MockDetail>(`/api/mock/${mockId}`),
  submitMockListening: (
    mockId: number,
    sessionId: string,
    answers: Record<string, string | number>,
  ) =>
    request<MockSubmitResult>(`/api/mock/${mockId}/listening/submit`, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, answers }),
    }),
  submitMockReading: (
    mockId: number,
    sessionId: string,
    answers: Record<string, string | number>,
  ) =>
    request<MockSubmitResult>(`/api/mock/${mockId}/reading/submit`, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, answers }),
    }),
  submitMockWriting: (
    mockId: number,
    task1Text: string,
    task2Text: string,
    durationSeconds: number,
  ) =>
    request<MockWritingSubmitResult>(`/api/mock/${mockId}/writing/submit`, {
      method: "POST",
      body: JSON.stringify({
        task1_text: task1Text,
        task2_text: task2Text,
        duration_seconds: durationSeconds,
      }),
    }),
  completeMockSpeaking: (
    mockId: number,
    setId: string,
    durationSeconds: number,
    bandLow?: number,
    bandHigh?: number,
  ) =>
    request<MockSpeakingCompleteResult>(
      `/api/mock/${mockId}/speaking/complete`,
      {
        method: "POST",
        body: JSON.stringify({
          set_id: setId,
          duration_seconds: durationSeconds,
          ...(bandLow !== undefined && bandHigh !== undefined
            ? { band_low: bandLow, band_high: bandHigh }
            : {}),
        }),
      },
    ),
  /* In-app feedback loop (Phase 4) */
  submitFeedback: (payload: {
    category: FeedbackCategory;
    message: string;
    page?: string | null;
  }) =>
    request<Feedback>("/api/feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  myFeedback: () => request<Feedback[]>("/api/feedback"),
  listFeedbackAdmin: (resolved?: boolean) =>
    request<Feedback[]>(
      resolved === undefined
        ? "/api/feedback/admin"
        : `/api/feedback/admin?resolved=${resolved}`,
    ),
  setFeedbackResolved: (id: number, resolved: boolean) =>
    request<Feedback>(`/api/feedback/admin/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ resolved }),
    }),
};
