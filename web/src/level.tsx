import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "./api";

// The CEFR level the skill screens (Path, Read&Listen, Write, Mock) read from.
// Seeded from the learner's progress level on first load, then a manual choice
// sticks via localStorage. The dropdown only offers levels that have content.

const STORAGE_KEY = "tef.level";

type LevelCtx = {
  level: string;
  levels: string[];
  setLevel: (l: string) => void;
};

const Ctx = createContext<LevelCtx | null>(null);

export function LevelProvider({ children }: { children: ReactNode }) {
  const [levels, setLevels] = useState<string[]>([]);
  const [level, setLevelState] = useState<string>(() => localStorage.getItem(STORAGE_KEY) || "a1");

  const setLevel = (l: string) => {
    localStorage.setItem(STORAGE_KEY, l);
    setLevelState(l);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [available, me] = await Promise.all([
        api.levels().then((r) => r.levels).catch(() => [] as string[]),
        api.me().catch(() => null),
      ]);
      if (cancelled) return;
      setLevels(available);
      // Only seed from the learner's level when they haven't chosen one yet.
      const persisted = localStorage.getItem(STORAGE_KEY);
      let next = persisted ?? me?.level ?? available[0] ?? "a1";
      if (available.length && !available.includes(next)) next = available[0];
      setLevelState(next);
      if (persisted == null) localStorage.setItem(STORAGE_KEY, next);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return <Ctx.Provider value={{ level, levels, setLevel }}>{children}</Ctx.Provider>;
}

export function useLevel(): LevelCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useLevel must be used within LevelProvider");
  return c;
}

export function LevelSwitcher() {
  const { level, levels, setLevel } = useLevel();
  // Nothing to switch between until more than one level has content.
  if (levels.length < 2) return null;
  return (
    <label className="level-switch">
      <span className="muted" style={{ fontSize: 12 }}>Level</span>
      <select value={level} onChange={(e) => setLevel(e.target.value)} aria-label="Level">
        {levels.map((l) => (
          <option key={l} value={l}>{l.toUpperCase()}</option>
        ))}
      </select>
    </label>
  );
}
