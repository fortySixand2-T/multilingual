// Thin typed client over the FastAPI backend. JWT lives in localStorage.
const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";
const TOKEN_KEY = "tef_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// Audio is auth-protected, and <audio src> can't send the Bearer header —
// so fetch the bytes with auth and hand back an object URL.
export async function fetchAudioUrl(path: string): Promise<string> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "audio fetch failed");
  return URL.createObjectURL(await res.blob());
}

// --- shapes (subset of what the backend returns) ---
export type TokenResponse = { access_token: string; token_type: string };
export type Unit = {
  id: string;
  title: string;
  icon: string;
  lessons: string[];
  unlock: { type: string; requires: string[] };
  status: "locked" | "available" | "complete";
};
export type PathView = { level: string; units: Unit[] };
export type Exercise = Record<string, any> & { id: string; type: string };
export type Lesson = {
  id: string;
  title: string;
  grammar_point?: string;
  pass_threshold?: number;
  new_vocab?: string[];
  exercises: Exercise[];
};
export type LessonResult = {
  lesson_id: string;
  passed: boolean;
  first_time: boolean;
  streak: number;
  xp: number;
};
export type DueCard = { card_key: string; due: string; vocab: { fr: string; en: string } | null };
export type Me = { user_id: number; level: string; xp: number; streak: number; last_active: string | null };
export type BoardMember = { user_id: number; display_name: string; level: string; xp: number; streak: number };
export type Drill = {
  lesson_id: string;
  over_budget: boolean;
  drill: string;
  provider: string;
  model: string;
  tokens_used_today: number;
  daily_budget: number;
};

export type CompSetSummary = {
  id: string;
  skill: "reading" | "listening";
  title: string;
  accent: string | null;
  time_limit_seconds: number | null;
  allow_replay: boolean;
  questions: number;
};
export type CompQuestion = { id: string; prompt: string; options: string[] };
export type CompSetView = {
  id: string;
  skill: "reading" | "listening";
  title: string;
  level: string;
  time_limit_seconds: number | null;
  allow_replay: boolean;
  accent: string | null;
  questions: CompQuestion[];
  passage?: string;
  audio_url?: string;
};
export type CompQResult = {
  question_id: string;
  correct: boolean;
  your_answer: string | null;
  correct_answer: string;
  explain: string;
};
export type CompResult = {
  set_id: string;
  score: number;
  correct: number;
  total: number;
  passed: boolean;
  first_pass: boolean;
  over_time: boolean;
  results: CompQResult[];
};

export const api = {
  signup: (b: { email: string; password: string; invite_code: string; display_name: string }) =>
    req<TokenResponse>("/auth/signup", { method: "POST", body: JSON.stringify(b) }),
  login: (b: { email: string; password: string }) =>
    req<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(b) }),

  path: (level = "a1") => req<PathView>(`/content/path?level=${encodeURIComponent(level)}`),
  lesson: (id: string) => req<Lesson>(`/content/lessons/${encodeURIComponent(id)}`),
  submitResult: (id: string, score: number) =>
    req<LessonResult>(`/progress/lessons/${encodeURIComponent(id)}/result`, {
      method: "POST",
      body: JSON.stringify({ score }),
    }),

  queue: (limit = 20) => req<{ due: DueCard[] }>(`/srs/queue?limit=${limit}`),
  review: (card_key: string, rating: "again" | "hard" | "good" | "easy") =>
    req<{ card_key: string; due: string }>("/srs/review", {
      method: "POST",
      body: JSON.stringify({ card_key, rating }),
    }),

  me: () => req<Me>("/progress/me"),
  board: () => req<{ members: BoardMember[] }>("/progress/board"),

  drill: (lesson_id: string, attempt?: string) =>
    req<Drill>("/tutor/drill", { method: "POST", body: JSON.stringify({ lesson_id, attempt }) }),

  comprehensionSets: (level = "a1", skill?: "reading" | "listening") =>
    req<{ sets: CompSetSummary[] }>(
      `/comprehension/sets?level=${encodeURIComponent(level)}${skill ? `&skill=${skill}` : ""}`
    ),
  comprehensionSet: (id: string) => req<CompSetView>(`/comprehension/sets/${encodeURIComponent(id)}`),
  submitComprehension: (id: string, answers: Record<string, string>, elapsed_seconds: number) =>
    req<CompResult>(`/comprehension/sets/${encodeURIComponent(id)}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers, elapsed_seconds }),
    }),
};
