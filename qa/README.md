# QA loop — tester agents → issue backlog → dev fixer

Multiple **tester agents** use the running app as different user personas, log every
problem as an action item in `qa/issues/`, and a **dev-fixer agent** works that
backlog (reproduce → fix with a test → mark done → commit).

## Run a round

1. **Start the app** (both servers):
   ```bash
   ./start.sh serve            # backend :9000  (in one terminal)
   cd web && npm run dev       # SPA :5173      (in another)
   ```
   Seed content first if needed: `./start.sh migrate && ./start.sh content-sync a1`
   (also `comprehension-sync`, `writing-sync`, `exam-sync`).

2. **Spawn testers** — one per persona. In Claude Code:
   > "Use the qa-tester agent with persona `absolute-beginner`."
   Run several (in parallel) across `qa/personas/`. Each files issues into `qa/issues/`.

3. **Fix** — when the backlog has items:
   > "Use the dev-fixer agent to work the QA backlog."

## Issue backlog

- One file per problem: `qa/issues/NNN-slug.md` (copy `qa/issues/TEMPLATE.md`).
- Status lives in frontmatter: `open` → `in-progress` → `done` (or `cannot-reproduce`).
- Severity: `blocker` (can't proceed) > `high` (broken/ wrong) > `medium` (confusing/
  rough) > `low` (polish). Triage high-severity first.

## Scope note

Drill, Writing grading, and Speaking need an LLM/STT/TTS provider configured. With
none set, a clean `503` there is expected — testers only file it if the *handling*
is poor, not for the missing provider itself.
