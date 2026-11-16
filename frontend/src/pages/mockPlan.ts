/* Mock plan: which test and writing prompts a mock sitting uses.

The mock detail endpoint does not carry the test/prompt ids, so the
runner remembers them from the start response (localStorage, this
device only). If that stored plan is missing — e.g. the learner
resumes a mock on another device — the plan is re-derived from the
backend's own rotation: mocks of a track use test pairs in order
(L1/RA1, L2/RA2, L3/RA3 for Academic; L1/RG1, L2/RG1, L3/RG1 for
General) and the first unused writing prompt of each task, in
definition order, which is the same as the n-th mock using the n-th
prompt (wrapping). The stored plan always wins over the derivation.
*/

import type {
  MockStartResponse,
  MockSummary,
  MockTrack,
  WritingPromptSummary,
} from "../api";

export interface MockPlan {
  listening_test_id: string;
  reading_test_id: string;
  writing_task1_prompt_id: string;
  writing_task2_prompt_id: string;
}

const ACADEMIC_PAIRS: Array<[string, string]> = [
  ["L1", "RA1"],
  ["L2", "RA2"],
  ["L3", "RA3"],
];

const GENERAL_PAIRS: Array<[string, string]> = [
  ["L1", "RG1"],
  ["L2", "RG1"],
  ["L3", "RG1"],
];

function planKey(mockId: number): string {
  return `prepsathi_mock_plan_${mockId}`;
}

export function saveMockPlan(
  mockId: number,
  plan: MockStartResponse | MockPlan,
): void {
  try {
    const stored: MockPlan = {
      listening_test_id: plan.listening_test_id,
      reading_test_id: plan.reading_test_id,
      writing_task1_prompt_id: plan.writing_task1_prompt_id,
      writing_task2_prompt_id: plan.writing_task2_prompt_id,
    };
    localStorage.setItem(planKey(mockId), JSON.stringify(stored));
  } catch {
    /* Private mode or full storage: the rotation fallback still works. */
  }
}

export function loadMockPlan(mockId: number): MockPlan | null {
  try {
    const raw = localStorage.getItem(planKey(mockId));
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed === "object" &&
      typeof (parsed as MockPlan).listening_test_id === "string" &&
      typeof (parsed as MockPlan).reading_test_id === "string" &&
      typeof (parsed as MockPlan).writing_task1_prompt_id === "string" &&
      typeof (parsed as MockPlan).writing_task2_prompt_id === "string"
    ) {
      return parsed as MockPlan;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Re-derive a mock's plan from its position among the same track's
 * mocks (oldest first). Needs the full mock list and the writing
 * prompts of the track, in definition order.
 */
export function deriveMockPlan(
  mockId: number,
  track: MockTrack,
  mocks: MockSummary[],
  prompts: WritingPromptSummary[],
): MockPlan | null {
  const sameTrack = [...mocks]
    .filter((m) => m.track === track)
    .sort(
      (a, b) =>
        Date.parse(a.started_at) - Date.parse(b.started_at) ||
        a.mock_id - b.mock_id,
    );
  const index = sameTrack.findIndex((m) => m.mock_id === mockId);
  if (index < 0) return null;
  const pairs = track === "academic" ? ACADEMIC_PAIRS : GENERAL_PAIRS;
  const [listening_test_id, reading_test_id] =
    pairs[index % pairs.length];
  const task1 = prompts
    .filter((p) => p.task === 1)
    .map((p) => p.id);
  const task2 = prompts
    .filter((p) => p.task === 2)
    .map((p) => p.id);
  if (task1.length === 0 || task2.length === 0) return null;
  return {
    listening_test_id,
    reading_test_id,
    writing_task1_prompt_id: task1[index % task1.length],
    writing_task2_prompt_id: task2[index % task2.length],
  };
}

/* ------------------------------------------------------------------ */
/* Section results remembered on this device, so the results page can  */
/* show per-question and per-criterion feedback after a reload. The   */
/* server keeps only the bands; these details live here only.          */
/* ------------------------------------------------------------------ */

export interface StoredScoredResult {
  score_raw: number;
  band_estimate: number;
  duration_seconds: number;
  results: Array<{
    no: number;
    correct: boolean;
    your_answer: string | number | null;
    correct_answer: string | number | null;
    explanation: string;
    evidence: string;
  }>;
}

export interface StoredWritingTask {
  word_count: number;
  min_words: number;
  meets_minimum: boolean;
  feedback: {
    band_low: number;
    band_high: number;
    criteria: Record<
      string,
      { band_low: number; band_high: number; notes: string[] }
    >;
    limits: string;
  };
}

export interface StoredMockResults {
  listening?: StoredScoredResult;
  reading?: StoredScoredResult;
  writing?: {
    task1: StoredWritingTask;
    task2: StoredWritingTask;
    writing_band_low: number;
    writing_band_high: number;
  };
}

function resultsKey(mockId: number): string {
  return `prepsathi_mock_results_${mockId}`;
}

export function loadMockResults(mockId: number): StoredMockResults {
  try {
    const raw = localStorage.getItem(resultsKey(mockId));
    if (!raw) return {};
    return JSON.parse(raw) as StoredMockResults;
  } catch {
    return {};
  }
}

export function saveMockResults(
  mockId: number,
  patch: Partial<StoredMockResults>,
): void {
  try {
    const merged = { ...loadMockResults(mockId), ...patch };
    localStorage.setItem(resultsKey(mockId), JSON.stringify(merged));
  } catch {
    /* Non-fatal: the results page falls back to the server bands. */
  }
}
