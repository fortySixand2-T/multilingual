---
id: 600
title: Dismissing the "review last conversation" nudge silently suppresses it for all later sessions, not just the current one
severity: high
area: web
persona: returning-learner
status: rejected
found: 2026-08-02
---

## Steps to reproduce
1. As a user with at least one prior `speech_turns` row that has a `session_id`
   (seeded directly via sqlite for this test: `user_id=172`, `session_id=prior-test-1`),
   log in and open `/speaking`.
2. Confirm the nudge "Review words from your last conversation" / "Not now" renders
   above the transcript (it does — `GET /speech/last-session?exclude=<sid>` returns
   `{"session_id":"prior-test-1"}`).
3. Click "Not now" to dismiss the nudge. It disappears — correct so far.
4. Without reloading the page, click a topic card (e.g. "Les voyages en avion") to
   start a new session — this triggers a brand new `sessionId` and a fresh
   `GET /speech/last-session?exclude=<new-sid>` call.
5. Observe the network response: it still correctly returns
   `{"session_id":"prior-test-1"}` (confirmed via curl with the same token/exclude
   value used by the page).
6. Observe the rendered page: **no nudge appears at all**, even though a legitimate,
   non-dismissed prior session exists for this new session context. Repeated for a
   second topic switch and for "Change topic" back to the topic-picker view — the
   nudge never returns for the rest of the page's lifetime.
7. Control check: on a fresh full page reload (new React mount, nudge never
   dismissed), then immediately picking a topic without clicking "Not now" first,
   the nudge *does* correctly reappear after the topic switch. This isolates the bug
   to the dismiss action, not to topic-switching itself.

## Expected
Per the round plan's design intent (H6): "Not now" should only suppress the nudge
for the session it was dismissed on. Switching topics starts a new session, and
since `GET /speech/last-session` still returns a real, not-yet-reviewed prior
session for that new session, a fresh nudge should reappear.

## Actual
Once "Not now" is clicked, the nudge never renders again for any subsequent
session within that page load (verified across 3 further session/topic changes),
despite `/speech/last-session` continuing to return a valid `session_id` each time.
The dismissed state is apparently not scoped/reset per `sessionId` as the
`key={prior-<sid>}` remount pattern implies it should be — it looks like the
"dismissed" flag lives in a broader-scoped state (e.g. a ref or state that isn't
tied to `priorSession`) and leaks across the `useEffect([sessionId])` refetches.
A full page reload is the only way to see the nudge again, which is a poor
experience for a learner who dismisses one nudge and expects a *different*
conversation's nudge to still show up normally.

## Notes
- Reproduced 3 times with distinct new session ids (`e90cdd00…`, `35007091…`,
  `eda407a3…`), all still correctly resolving to `prior-test-1` server-side.
- Likely file: `web/src/screens/Speaking.tsx`, the `SessionReview`/nudge
  dismiss-state wiring around the `useEffect([sessionId])` that fetches
  `speechLastSession`.

## Triage
- Explanation: `SessionReview` is intentionally keyed on the *value* of
  `priorSession`, not on the current `sessionId`
  (`key={\`prior-${priorSession}\`}`, `web/src/screens/Speaking.tsx:150-159`).
  `dismissed` is local component state (`useState` inside `SessionReview`,
  line 237), so it only resets when React remounts the component — i.e. only
  when `priorSession`'s *value* changes to a different session id. In this
  repro, `user_id=172` has exactly one `speech_turns` row ever
  (`session_id=prior-test-1`; confirmed via `sqlite3 data/tef.db "select ...
  from speech_turns where user_id=172"` → single row). Because STT is
  unavailable in this environment (`/speech/status` → `{"available":false}`),
  no turn can ever be POSTed to `/speech/turn`, so switching topics never
  creates a new `speech_turns` row and `GET /speech/last-session` — confirmed
  live via curl with a freshly seeded second test user (`user_id=177`,
  `session_id=prior-triage-1`) — keeps resolving to the *same* prior session
  id regardless of the `exclude` value passed. The component never remounts
  because its key never changes, so the dismissal correctly persists for that
  one still-unreviewed conversation.
- Against spec: the round plan's own comment in the diff (`Speaking.tsx:148-149`,
  "Keyed by the prior session so it resets when that changes") describes
  exactly this value-based scoping as the intended design, not
  `sessionId`-based scoping. H6 in the round plan hypothesized dismissal
  should reset on topic switch, but that's only true when topic-switching
  actually produces a *new* prior session (i.e. after the learner has spoken
  in the interim session) — which requires STT, unavailable here.
- Verdict: rejected
- Rationale: Not a leak — it's the intended behavior (dismiss is scoped to
  the specific unreviewed conversation, not the viewing session). The repro
  only reproduces because no second conversation can ever be created in this
  STT-less environment, so `/speech/last-session` always resolves to the same
  id across every topic switch; a real learner who speaks in a new session
  before switching topics would see the key change and get a fresh nudge, as
  designed. Re-file only if reproduced with STT enabled (or two seeded
  sessions) showing dismissal persisting across a *genuinely new* prior
  session.


## Resolution
Rejected (confirmed against code). `dismissed` is local to `SessionReview`, which is keyed `prior-${priorSession}` — it resets only when the prior session's *value* changes. The repro only persists because this STT-less env can't create a new `speech_turns` row, so `/speech/last-session` always resolves to the same id and the component never remounts. A real learner who speaks a new conversation gets a new prior id → key change → fresh nudge, as designed. No fix.
