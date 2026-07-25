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

// FastAPI returns 422 validation errors as `detail: [{loc, msg, type}]`. Render those as
// a readable sentence instead of dumping raw JSON at the user (the backend's min/max/range
// checks all land here).
function readableError(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((e: any) => {
        if (!e?.msg) return null;
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : undefined;
        return field && field !== "body" ? `${field}: ${e.msg}` : e.msg;
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join("; ");
  }
  return fallback;
}

async function errorFrom(res: Response): Promise<ApiError> {
  let detail: unknown = res.statusText;
  try {
    detail = (await res.json()).detail ?? detail;
  } catch {
    /* non-JSON error */
  }
  return new ApiError(res.status, readableError(detail, res.statusText));
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
  if (!res.ok) throw await errorFrom(res);
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

export type SpeechTurnResult = {
  turn_id?: number;
  over_budget: boolean;
  transcript: string;
  reply_text?: string;
  reply_audio_url?: string | null;
  provider?: string;
  model?: string;
};
export type SpeechHistoryTurn = {
  turn_id: number;
  mode: string;
  transcript: string;
  reply_text: string;
  reply_audio_url: string | null;
};

// Multipart upload of recorded audio (FormData — don't set Content-Type by hand).
export async function postSpeechTurn(audio: Blob, mode: string): Promise<SpeechTurnResult> {
  const token = getToken();
  const form = new FormData();
  form.append("audio", audio, "turn.webm");
  form.append("mode", mode);
  const res = await fetch(`${BASE}/speech/turn`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) throw await errorFrom(res);
  return res.json();
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
  first_pass: boolean;
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
  xp: number;
  streak: number;
  results: CompQResult[];
};

export type WritingTaskSummary = {
  id: string;
  section: "A" | "B";
  title: string;
  prompt: string;
  min_words: number;
  max_words: number | null;
  target_vocab_fr?: string[];
};
export type CriterionScore = { name: string; score: number; comment: string };
export type InlineCorrection = { excerpt: string; correction: string; explanation: string; reference: string };
export type WritingFeedback = {
  clb_estimate: number;
  criteria: CriterionScore[];
  corrections: InlineCorrection[];
  overall: string;
};
export type WritingGrade = {
  task_id: string;
  over_budget: boolean;
  word_count: number;
  meets_min_words?: boolean;
  submission_id?: number;
  provider?: string;
  model?: string;
  feedback: WritingFeedback | null;
};

export type ExamSection = {
  skill: "reading" | "listening" | "writing" | "speaking";
  time_limit_seconds: number;
  comprehension_set_id?: string | null;
  writing_task_ids?: string[];
  speaking_prompts?: string[];
};
export type ExamBlueprint = { id: string; level: string; title: string; sections: ExamSection[] };
export type ExamBlueprintSummary = { id: string; title: string; sections: number };
export type ClbReport = {
  per_skill: Record<string, number>;
  overall: number | null;
  target_met: boolean;
  note: string;
};
export type ExamSectionResult = {
  skill: ExamSection["skill"];
  correct?: number;
  total?: number;
  clb_estimate?: number;
};
export type ExamAttemptSummary = {
  attempt_id: number;
  blueprint_id: string;
  level: string;
  status: string;
  clb_report: ClbReport | null;
  started_at: string;
  finished_at: string | null;
};

export type WeakSpot = {
  id: number;
  set_id: string;
  set_title: string;
  skill: string;
  question_id: string;
  prompt: string;
  options: string[];
  explain: string;
  times_missed: number;
};
export type WeakSpotAnswer = {
  correct: boolean;
  correct_answer: string;
  explain: string;
  resolved: boolean;
};

export type SkillReadiness = { best: number; recent: number; trend: number[] };
export type Readiness = {
  attempts: number;
  per_skill: Record<string, SkillReadiness>;
  overall: number | null;
  target_met: boolean;
  weakest_skill: string | null;
  target_clb: number;
};

export type VocabCard = {
  id: string;
  fr: string;
  en: string;
  level?: string;
  audio?: string;
  pos?: string;
  tags?: string[];
  gender?: "" | "m" | "f" | "mf"; // "" = not gendered
  fem?: string; // feminine spelling, present for gender "mf"
  fem_audio?: string; // feminine pronunciation key, present for gender "mf"
  known?: boolean;
  in_review?: boolean;
};

export type GrammarItem = {
  unit_id: string;
  unit_title: string;
  lesson_id: string;
  lesson_title: string;
  grammar_point: string;
  grammar_category: string; // grammatical family; "" if the lesson predates categories
};

export const api = {
  signup: (b: { email: string; password: string; invite_code: string; display_name: string }) =>
    req<TokenResponse>("/auth/signup", { method: "POST", body: JSON.stringify(b) }),
  login: (b: { email: string; password: string }) =>
    req<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(b) }),

  levels: () => req<{ levels: string[] }>("/content/levels"),
  path: (level = "a1") => req<PathView>(`/content/path?level=${encodeURIComponent(level)}`),
  grammar: (level = "a1") =>
    req<{ level: string; items: GrammarItem[] }>(
      `/content/grammar?level=${encodeURIComponent(level)}`,
    ),
  lesson: (id: string) => req<Lesson>(`/content/lessons/${encodeURIComponent(id)}`),
  // Omit `level` to fetch every level's vocab at once (each card carries its level).
  vocab: (level?: string, tag?: string) => {
    const q = new URLSearchParams();
    if (level) q.set("level", level);
    if (tag) q.set("tag", tag);
    const qs = q.toString();
    return req<{ cards: VocabCard[] }>(`/content/vocab${qs ? `?${qs}` : ""}`);
  },
  setKnown: (card_key: string, known: boolean) =>
    req<{ card_key: string; known: boolean }>("/content/vocab/known", {
      method: "POST",
      body: JSON.stringify({ card_key, known }),
    }),
  addToReview: (card_key: string) =>
    req<{ card_key: string; added: boolean }>("/srs/add", {
      method: "POST",
      body: JSON.stringify({ card_key }),
    }),
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

  writingTasks: (level = "a1", section?: "A" | "B") =>
    req<{ tasks: WritingTaskSummary[] }>(
      `/assessment/tasks?level=${encodeURIComponent(level)}${section ? `&section=${section}` : ""}`
    ),
  writingTask: (id: string) => req<WritingTaskSummary & { level: string }>(`/assessment/tasks/${encodeURIComponent(id)}`),
  submitWriting: (id: string, text: string) =>
    req<WritingGrade>(`/assessment/tasks/${encodeURIComponent(id)}/submit`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  speechHistory: () => req<{ turns: SpeechHistoryTurn[] }>("/speech/history"),

  readiness: () => req<Readiness>("/exam/readiness"),
  weakSpots: () => req<{ weak_spots: WeakSpot[] }>("/progress/weak-spots"),
  answerWeakSpot: (id: number, chosen: string) =>
    req<WeakSpotAnswer>(`/progress/weak-spots/${id}/answer`, {
      method: "POST",
      body: JSON.stringify({ chosen }),
    }),
  dismissWeakSpot: (id: number) =>
    req<{ id: number; resolved: boolean }>(`/progress/weak-spots/${id}/dismiss`, {
      method: "POST",
    }),
  examBlueprints: (level = "a1") => req<{ blueprints: ExamBlueprintSummary[] }>(`/exam/blueprints?level=${encodeURIComponent(level)}`),
  examStart: (blueprint_id: string) =>
    req<{ attempt_id: number; blueprint: ExamBlueprint }>("/exam/start", {
      method: "POST",
      body: JSON.stringify({ blueprint_id }),
    }),
  examAttempt: (attemptId: number) =>
    req<{
      attempt_id: number;
      blueprint: ExamBlueprint;
      status: string;
      recorded: string[];
      remaining: string[];
      clb_report: ClbReport | null;
    }>(`/exam/attempts/${attemptId}`),
  examSection: (attemptId: number, body: ExamSectionResult) =>
    req<{ skill: string; clb: number; recorded: string[] }>(`/exam/${attemptId}/section`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  examFinish: (attemptId: number) =>
    req<{ attempt_id: number; report: ClbReport; xp: number; streak: number }>(
      `/exam/${attemptId}/finish`,
      { method: "POST" },
    ),
  examHistory: () => req<{ attempts: ExamAttemptSummary[] }>("/exam/history"),
};
