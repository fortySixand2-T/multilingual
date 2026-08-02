# QA round 045 — plan

- date: 2026-08-01
- app under test: backend :9010 / SPA (vite dev server, single-origin proxy) :5173
- scope: Speaking feature push — slice 1 (topic bank, merged to main) + slice 2
  (faster response: STT device/compute knobs, examiner max_tokens cap), tested together
  on branch `feat/speaking-faster-stt`.

## Change surface (highest risk first)

- `app/speech/topics.py` — new module: `SpeakingTopic` model, `load_topics`
  (YAML → dict keyed by id, duplicate-id error), `framing` (section A vs B system-
  prompt addendum), `sync_topics` (delete-and-replace per level).
- `app/speech/tables.py` — new `SpeakingTopicRow`: **`id` is a bare `String(64)`
  primary key, not scoped by level.** `sync_topics` only deletes rows for the level
  being synced, so a duplicate id authored under two different levels would collide
  on insert (IntegrityError) — currently avoided only because every authored id is
  level-prefixed (`speak-a1-a-restaurant`, …), not because anything enforces it.
- `app/speech/api.py`:
  - `GET /speech/topics?level=&section=` — new, no ownership/level check beyond
    the SQL filter.
  - `POST /speech/turn` — new optional `topic_id` form field. Looked up with
    `session.get(SpeakingTopicRow, topic_id)` — **by id alone, with no check that
    the topic's `level` matches anything about the caller's current level.** A
    learner (or a scripted client) can pass a topic_id from a level/section they
    never fetched via `/speech/topics` and still get its framing injected into the
    examiner's system prompt.
  - `max_tokens=settings.examiner_max_tokens` now threaded into `examiner.turn(...)`.
- `app/speech/examiner.py` — `turn()` gained `max_tokens: int = 1024` (default only
  matters if a caller other than the API forgets to pass it) forwarded into
  `router.run(..., max_tokens=...)`.
- `app/speech/factory.py` / `app/config/settings.py` — `build_stt` now forwards
  `whisper_device` / `whisper_compute_type` to `FasterWhisperAdapter`; both default
  to the previous cpu/int8 behavior, so no behavior change when unset.
- `web/src/screens/Speaking.tsx` — new `TopicPicker`: level-scoped topic list,
  "Change topic" clears selection, topic cleared on level change (`useEffect` on
  `level`), record/mode controls disabled while `recording || busy`.
- `content/<level>/speaking/*.yaml` — 8 authored topics (2 per level, a1/a2 =
  Section A, b1/b2 = Section B); `speaking_topics` DB table via migration `0016`.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | api/data | A `topic_id` for a level/section never listed to the caller is still accepted and framed by `/speech/turn` (no ownership/level check on the id) — cross-level content leaks into the examiner prompt. | Sync topics for two levels; call `POST /speech/turn` with a `topic_id` that belongs to a level other than the one the test client "is on" (never called `/speech/topics?level=<that level>`); inspect whether framing still applies (use a capturing fake router if testing at unit level, or infer from behavior/response at HTTP level). | edge-case-breaker |
| H2 | data integrity | Two topics authored with the same `id` under different levels would break `sync_topics` for the second level with an unhandled IntegrityError (PK collision), since delete-and-replace is scoped to one level only. | Sync level X, then sync level Y with a topic file reusing an id from X (can be done via a temp content root against `sync_topics` directly, or by checking there's no id-uniqueness validation across levels in `load_topics`/`sync_topics`). Treat as a coverage-gap/robustness finding if reproducing needs a crafted fixture rather than the shipped content. | edge-case-breaker |
| H3 | api | `GET /speech/topics` with a `level` that has no synced topics, an unknown level string, or a bogus `section` value returns a clean empty list, not a 500 — and ordering is stable (`order_by(id)`). | `curl` various level/section combos including empty-string level, garbage section, level with zero topics. | edge-case-breaker |
| H4 | api/regression | Slice-2 wiring (`max_tokens`, device/compute knobs) hasn't regressed the existing hardened `/speech/turn` behavior: `/speech/status` preflight (qa-540), empty/oversized/undecodable audio, over-budget short-circuit, no-speech 422, and R10 (no audio persisted). | Re-run the existing hardened-input probes from qa-540/H9/R10 against the current branch's live endpoints (503 disabled-path is expected here; confirm it's still a clean 503 not a 500, and that `/speech/status` still says `available:false` before any recording is attempted). | edge-case-breaker |
| H5 | ui/ux | Topic picker: switching CEFR level clears the picked topic and re-fetches that level's topics (not stale); "Change topic" returns to the picker list; Section A vs Section B topics render with correct labels/points; controls are disabled while recording/busy; the "no topics for this level" case (picker section hidden — `topics.length === 0`) doesn't leave a dangling empty card. | Drive the Speaking screen in the browser: switch levels, pick a topic, check the task card, hit Change topic, try toggling mode while a topic is picked, resize to phone width. STT is disabled here so actual recording 503s — that's expected, not a bug; focus on the picker/task-card UI states which don't need STT. | absolute-beginner |
| H6 | ui/ux | Free-conversation path (no topic picked) still works end-to-end from the UI's perspective — Record button state, mode selector, and messaging make it clear a topic is optional, not required. | On the Speaking screen, don't pick a topic and confirm nothing blocks proceeding (modulo the STT-disabled 503), and that copy doesn't imply a topic is mandatory. | absolute-beginner |

## Coverage gaps

- No existing issue history for `/speech/topics` or the picker UI — this is new
  surface with zero prior QA passes.
- No test (unit or otherwise) exercises a `topic_id` from a level other than the
  one currently being queried (H1) — the closest existing test
  (`test_unknown_topic_id_is_ignored_not_an_error`) only covers a nonexistent id,
  not a *valid id from a different level*.
- No test for duplicate topic id across levels (H2).
- Frontend has no test file for `Speaking.tsx` / `TopicPicker` at all
  (`web/src/screens/*.test.tsx` — check if one exists; if not, that's itself a gap
  worth noting, not necessarily filing).

## Charters (per tester, with id blocks)

- `edge-case-breaker` via `qa-tester` (ids 550–559): chase H1, H2, H3, H4. Backend
  at `http://127.0.0.1:9010`. Auth: use whatever invite-code signup flow existing
  tests/personas use (`INVITE_CODES=friend-001,friend-002` is set on the running
  server). Sync topics for at least two levels before probing (already synced:
  a1/a2/b1/b2, 2 topics each). Use `python -m app.speech.topics <level>` only if
  you need to reseed; don't wipe existing data other testers may rely on.
- `absolute-beginner` via `qa-browser-tester` (ids 560–569): chase H5, H6. App at
  `http://127.0.0.1:5173` (SPA dev server, `/api` proxied to the :9010 backend
  single-origin — use this origin, not :9010 directly, for the browser). Sign up /
  log in as needed, navigate to Speaking, and work the topic picker across at
  least two levels. Do not attempt to grant real mic access or expect a working
  recording round-trip — `/speech/status` reports `available:false` here by
  design (STT disabled in dev); that's environment, not a bug.

## Don't re-file (already settled)

- 540 (mic requested before availability check) — already fixed (`status: done`);
  slice-2 didn't touch the preflight logic, but re-verify it still works, don't
  re-file it as new.
- 394 (level-filtered endpoints accept empty-string level) — rejected pattern;
  don't re-file an empty-string-`level` variant against `/speech/topics` as a
  standalone issue unless it actually 500s (a clean empty list is fine, per H3).
- 360 / 251 (level param silently ignored on other endpoints) — rejected pattern;
  a *lenient* level filter is not itself a bug in this codebase. H1's concern is
  different in kind — it's about `topic_id` acting as an unscoped object reference
  into the examiner's prompt, not about a list filter being loose.
- Drill / Writing / Speaking 503 with no provider — expected; STT/TTS disabled in
  this dev environment is the documented, expected state.

## Outcomes

- H1 (cross-level topic_id ownership check): **untested — unobservable in this
  environment.** `app/speech/api.py::speech_turn` raises 503 for STT-disabled
  before the `topic_id` lookup is ever reached, so this can't be exercised over
  HTTP while STT is disabled in dev. Confirmed by both code reading and live curl
  probes (edge-case-breaker). Worth revisiting once STT is enabled somewhere
  (staging/prod), or by adding a unit test that calls `SpeakingExaminer`/the
  lookup logic directly with a fake STT, bypassing the 503 gate.
- H2 (duplicate topic id across levels crashes sync): **confirmed** → issue 550
  (`speaking-topic-id-collision-across-levels-crashes-sync`), reproduced twice
  independently in an isolated scratch DB. Critic-gated verdict: **deferred** —
  it's a pre-existing repo-wide content-sync pattern (same shape in
  `app/assessment/tables.py`/`sync.py` for writing tasks), not a regression from
  this PR, and unreachable today since all authored ids are level-prefixed by
  convention. Recommended as a cross-cutting backlog item, not a one-off patch.
- H3 (`/speech/topics` edge cases): **refuted** (area sound) — unknown level,
  empty level, garbage/missing section all return clean 200s with correct
  filtering/ordering; missing required `level` query param correctly 422s. No
  500s found.
- H4 (regression check on hardened `/speech/turn` behavior): **refuted** (area
  sound) — `/speech/status` still 200s `{"available": false}`; auth (401) is
  clean with no/garbage token; no 500s anywhere. The specific empty/oversized/
  garbage-audio validations are unreachable via curl here (STT-disabled 503 fires
  first), same caveat as H1 — not a regression, just untestable in this
  environment.
- H5 (topic picker level-scoping / UI states): **confirmed** — level switch
  correctly clears the picked topic and reloads that level's topics; task card
  renders title/prompt/section/points correctly; "Change topic" returns to the
  picker; layout held up down to ~606px (couldn't force true 320px in this
  browser-automation environment). Along the way, found and → issue 560
  (`speaking-instruction-hint-ignores-picked-topic`): the static "introduce
  yourself" hint under Record never updates once a topic is picked. Critic-gated
  verdict: **validated**, fixed this round (see below). The "level with zero
  topics" sub-case remains untested — a1/a2/b1/b2 all have topics, and invalid
  levels fall back to a1.
- H6 (free-conversation path is clearly optional): **confirmed** — nothing on the
  screen implies a topic must be picked; copy reads as optional to a beginner
  persona. Also surfaced issue 561 (`speaking-topic-prompts-no-beginner-support`,
  topic prompts are 100% French with no gloss/scaffold) — critic-gated verdict:
  **deferred**, a real but out-of-scope spec gap (beginner-support UX), not a
  defect in this topic-bank PR's remit.

## Issues filed this round

- 550 — speaking-topic-id-collision-across-levels-crashes-sync — **deferred**
  (cross-cutting content-sync pattern, unreachable with today's content)
- 560 — speaking-instruction-hint-ignores-picked-topic — **validated → fixed**
  (commit `b3771c6` on `feat/speaking-faster-stt`)
- 561 — speaking-topic-prompts-no-beginner-support — **deferred** (real gap,
  out of scope for this PR)

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
