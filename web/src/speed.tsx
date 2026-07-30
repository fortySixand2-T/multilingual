import { createContext, useContext, useState, ReactNode } from "react";

// The playback rate for the 🐢 slow-replay buttons, shared across every audio
// player (vocab, review, listen drills, examiner replies). Learners who find the
// baked-in clips too fast can dial this down; the choice sticks via localStorage.
// Pitch is preserved at playback time, so slower stays clear rather than droning.

const STORAGE_KEY = "tef.slowRate";

// Offered steps, fastest → slowest. 0.5× is the floor (half speed).
export const SLOW_RATES = [0.9, 0.8, 0.7, 0.6, 0.5] as const;
const DEFAULT_RATE = 0.7;

function load(): number {
  const v = Number(localStorage.getItem(STORAGE_KEY));
  return SLOW_RATES.includes(v as (typeof SLOW_RATES)[number]) ? v : DEFAULT_RATE;
}

type SpeedCtx = {
  slowRate: number;
  setSlowRate: (r: number) => void;
};

// Default context so audio players work even when rendered outside a provider
// (e.g. isolated component tests); only the header control needs a live setter.
const Ctx = createContext<SpeedCtx>({ slowRate: DEFAULT_RATE, setSlowRate: () => {} });

export function SpeedProvider({ children }: { children: ReactNode }) {
  const [slowRate, setRate] = useState<number>(load);
  const setSlowRate = (r: number) => {
    localStorage.setItem(STORAGE_KEY, String(r));
    setRate(r);
  };
  return <Ctx.Provider value={{ slowRate, setSlowRate }}>{children}</Ctx.Provider>;
}

export function useSlowRate(): SpeedCtx {
  return useContext(Ctx);
}

// Header control for choosing how slow the 🐢 buttons play.
export function SlowSpeedControl() {
  const { slowRate, setSlowRate } = useSlowRate();
  return (
    <label className="level-switch">
      <span className="muted" style={{ fontSize: 12 }}>🐢 Slow</span>
      <select
        value={slowRate}
        onChange={(e) => setSlowRate(Number(e.target.value))}
        aria-label="Slow playback speed"
      >
        {SLOW_RATES.map((r) => (
          <option key={r} value={r}>{`${r}×`}</option>
        ))}
      </select>
    </label>
  );
}
