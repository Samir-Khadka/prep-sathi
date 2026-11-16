/* PrepSathi API client. The token lives in localStorage; nothing
   sensitive is ever written into the code itself. */

const API_URL =
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
}

export interface VocabularyItem {
  id: number;
  word: string;
  meaning: string;
  topic: string;
  interval_days: number;
  next_review: string;
  created_at: string;
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
};
