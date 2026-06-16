# TEF Prep — Web (Phase 1)

Duolingo-style SPA (Vite + React + TypeScript) for the A1 learning loop. Talks to
the FastAPI backend over `/api/*` (proxied in dev; see `vite.config.ts`).

## Run

```bash
# 1. backend on :9000 (from the repo root)
./start.sh migrate
./start.sh content-sync a1
./start.sh serve

# 2. frontend
cd web
npm install
npm run dev          # http://localhost:5173  (proxies /api -> :9000)
```

Sign up with an invite code from the backend's `INVITE_CODES`, then the loop is:
**Learn** (path → lesson exercises → complete) → unlocks the next unit, seeds new
words into **Review** (SRS), bumps your streak/XP on the **Group** board.
**Drill** asks the tutor for a scaffolded practice item (needs an LLM provider
configured; falls back gracefully when over the daily budget).

## Screens
- `screens/Path.tsx` — the unit path with locked/available/complete gating.
- `screens/Lesson.tsx` — exercise player (mcq, word_bank, listen_type, match_pairs, translate).
- `screens/Review.tsx` — SRS flashcard queue.
- `screens/Drill.tsx` — tutor drill.
- `screens/GroupBoard.tsx` — cooperative leaderboard.

## Notes
- `listen_type` shows the clip id but audio isn't served yet (Phase 2 audio pipeline).
- Exercise answers are checked client-side from authored content — fine for a
  closed-group study tool; not exam-secure.
