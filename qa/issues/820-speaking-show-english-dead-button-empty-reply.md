---
id: 820
title: "Show English" button silently does nothing for a turn with blank reply_text
severity: medium
area: web
persona: absolute-beginner
status: done
found: 2026-09-12
---

## Steps to reproduce
1. Sign in to an account that has a speech turn whose `reply_text` is an empty
   string (e.g. `turn_id 2` in the seeded QA data for user 1 — session shows
   "You said: test transcript" followed by an "Examiner" bubble with no French
   text under the "Examiner" label at all).
2. Go to Speaking, scroll to that turn in the conversation history.
3. Click "Show English" under that (textless) Examiner bubble.

## Expected
Either: (a) no "Show English" button is rendered at all for a turn with no
examiner reply text (there's nothing to translate), or (b) pressing it gives some
visible feedback — e.g. a message like "Nothing to translate for this turn" —
so the learner knows the click registered.

## Actual
Clicking "Show English" briefly shows no change (button never visibly flips to
"Hide English" or shows any text/error). Confirmed via direct API call that this
is because the backend returns `{"reply_en": "", "cached": true}` for this turn —
an empty string. In `web/src/screens/Speaking.tsx`, `Subtitle`'s render guard is
`if (shown && replyEn)`, and `reveal()` sets `shown(true)` and calls
`onTranslated("")`, but since `replyEn` is falsy (empty string), the component
still falls through to rendering the "Show English" button again on the next
render. The result: the button appears to do nothing at all — no error, no
"nothing to show" message, no visual state change of any kind. An absolute-
beginner persona would reasonably conclude the button/feature is broken.

## Notes
- Confirmed via `POST /speech/turn/2/translate` directly: returns
  `{"reply_en":"","cached":true}`, HTTP 200 — not an error path, so the `catch`
  block's "Couldn't load the English just now." message never fires either.
- This is the exact lead flagged in `qa/rounds/057-plan.md` H7 ("concrete lead,
  not just a hypothesis") — confirmed reachable and reproducible through the real
  UI with the seeded turn (turn_id 2, empty `reply_text`), not just a
  theoretical code-read concern.
- Relevant code: `Subtitle` component, `web/src/screens/Speaking.tsx` around
  lines 639-695, especially the `if (shown && replyEn)` guard vs. `reveal()`'s
  unconditional `setShown(true)`.
- Suggested fix direction: don't render the "Show English" control at all when
  the turn has no `reply_text`/nothing meaningful to translate, or track "has
  attempted to reveal, got nothing" as separate state from `shown` so a
  no-content message can render instead of silently resetting.

## Triage
- Explanation: `POST /speech/turn/{turn_id}/translate` (app/speech/api.py:461-518)
  has an explicit early-return `if not turn.reply_text.strip(): return
  {"reply_en": "", "cached": True}` (line 491-492) — a blank `reply_text`
  is an anticipated backend state, not a fluke of the seeded turn. The same
  file guards audio synthesis identically at lines 203, 284, and 410
  (`if tts is None or not turn.reply_text.strip()`), and the daily-budget
  path at line 496-497 also returns `{"reply_en": "", "over_budget": true}` —
  another 200-with-empty-string shape. On the frontend, `Subtitle` in
  web/src/screens/Speaking.tsx (639-698) is rendered unconditionally per turn
  (no gate on `t.reply_text` at the call site, line 268), and its render guard
  is `if (shown && replyEn)` (line 678) while `reveal()` unconditionally does
  `onTranslated(r.reply_en); setShown(true)` (668-669) whenever `over_budget`
  is falsy — so a `""` reply_en satisfies neither the "translated" branch
  (falsy `replyEn`) nor the `failed` message branch (only set for
  `over_budget`/catch), leaving the button re-rendered with zero feedback.
  This is the exact bug described: a real latent gap in the falsy-string guard,
  not an artifact of how the turn was seeded.
- Against spec: the technical plan's Speaking flow doesn't call out empty-reply
  handling explicitly, but the codebase's own defensive checks (reply_text.strip()
  guards in 3 places server-side) show blank examiner replies are treated as a
  first-class, expected state to handle gracefully — the UI just misses this one
  spot. General UX principle applies: every user-initiated action needs visible
  feedback, which this violates.
- Reachability in production: plausible, not just seeded-only. Paths that can
  legitimately produce an empty `reply_text`/`reply_en` in prod: (1) a
  degenerate/failed LLM completion for the examiner turn (empty string is a
  known failure mode for chat completions, especially under content filters or
  truncation-at-zero-tokens); (2) hitting `speaking_daily_token_budget` during
  the *translate* call specifically produces `{"reply_en": "", "over_budget":
  true}` today, which *is* handled by `Subtitle` (line 666 sets `failed`) —
  so that particular path already works. The genuinely-uncovered path is
  turn.reply_text itself being blank/whitespace-only, which requires the
  examiner-generation call (not the translate call) to have produced an empty
  reply — rarer, but the server code (three separate `.strip()` guards) treats
  it as something that happens, not something impossible. So while the QA
  turn was seeded directly into SQLite for convenience, the code path it
  exercises is real and not test-artifact-only.
- Verdict: validated
- Rationale: user impact — an absolute-beginner learner who hits a genuinely
  blank examiner reply (rare but anticipated by the backend's own guards) gets
  a "Show English" button that silently does nothing on every click, with no
  error and no state change, which reads as a broken feature rather than "there
  is nothing to translate here." Low-frequency but real gap in a widely-used
  Speaking screen; worth the small fix (skip rendering Subtitle when
  `reply_text` is blank, or add a "nothing to translate" message) since the
  fix is cheap and the current behavior actively misleads the user about
  whether their click registered.

## Critic
- Challenge: the strongest case for "no change" is that this is entirely
  self-inflicted: the only way to reach a blank `reply_text` in the seeded QA
  run was a direct SQLite insert (`turn_id 2`), not anything the app itself can
  produce. Real conversations always go through `POST /speech/turn` (transcribe
  → LLM reply), and that endpoint already refuses to persist a blank turn when
  the *learner's* audio is silent (the `no_speech` guard, `app/speech/api.py`
  around line 183, with the H9 comment "reject cleanly so we never persist a
  blank turn"). If the app never lets a blank turn through, this is a QA-seed
  artifact and the fix is churn for a state that can't occur.
- Holds up? No — the "no_speech" guard only covers the *learner's* transcript
  being empty; it says nothing about the *examiner's* LLM reply being empty. I
  read `SpeakingExaminer.turn()` (`app/speech/examiner.py:117-168`) directly:
  after STT succeeds and the no_speech bail-out is cleared, the code calls
  `self._router.run(...)` and then unconditionally does
  `return TurnResult(False, transcript.text, reply.text, ...)` and the caller
  persists `reply_text=result.reply_text` (`app/speech/api.py:186-196`) with
  **no check that `reply.text` is non-blank**. A zero-token/degenerate/
  content-filtered LLM completion (a real, if infrequent, failure mode for
  chat completions) would sail straight through into a persisted turn with
  blank `reply_text` — the exact shape the seeded row stands in for. The
  seeding was a shortcut to *reach* that state quickly, not a fabrication of a
  state the app can't otherwise produce, so the "self-inflicted only" attack
  fails on direct inspection of `examiner.py`.
  I also hand-traced the frontend state machine in `Subtitle`
  (`web/src/screens/Speaking.tsx:639-698`) rather than trusting the PM's
  prose: `shown` inits to `Boolean(replyEn)` = `false` for `replyEn=""`;
  clicking calls `reveal()`, which (since `replyEn` is falsy) skips the early
  return, calls the API, gets back `{reply_en:"", cached:true}` with
  `over_budget` falsy, so it takes the `else` branch — `onTranslated("")` then
  `setShown(true)` — and the very next render evaluates
  `if (shown && replyEn)` with `shown=true, replyEn=""`, which is falsy, so it
  falls through to rendering the "Show English" button again. This is a
  deterministic boolean-logic bug, not a rendering/CSS ambiguity that needs a
  screenshot to adjudicate — the two branches are mutually exclusive on a
  falsy empty string, full stop. No browser repro changes that conclusion.
  On cost: the suggested fix (skip rendering `Subtitle` when the turn's
  `reply_text` is blank, or track "attempted, got nothing" as separate state)
  is a small, local, low-complexity change — it does not trade simplicity for
  robustness in a way CLAUDE.md's DRY/simple guidance would object to.
  Severity stays proportionate at `medium`: rare trigger, but when it fires it
  reads as a broken button with zero feedback to an absolute-beginner learner,
  which is a real (not cosmetic) UX defect once it happens.
- Final verdict: validated

## Fix
Reproduced by seeding a turn with `reply_text=""` and calling
`Subtitle`'s `reveal()` with a mocked `speechTranslate` returning
`{"reply_en": "", "cached": true}` — the button re-rendered with zero
feedback, exactly as reported.

Two changes in `web/src/screens/Speaking.tsx`:
1. At the turn-list call site, don't render `Subtitle` at all when
   `t.reply_text` is blank/whitespace-only — there's nothing to translate,
   so no control is offered (matches option (a) from the Notes).
2. In `Subtitle.reveal()`, if the translate call succeeds (not
   `over_budget`) but comes back with an empty `reply_en` anyway (e.g. a
   non-blank `reply_text` that itself translates to nothing, or any other
   path reaching this state), set `failed` to
   "Nothing to translate for this turn." instead of silently falling
   through — covers option (b) as a defense-in-depth for cases not caught
   by (1).

Added regression tests to `web/src/screens/Speaking.test.tsx`
("Speaking subtitle with a blank examiner reply (qa-820)"): one asserting
no "Show English" button renders for a turn with `reply_text: ""`, one
asserting the no-content message appears (and the button doesn't vanish
without explanation) when `speechTranslate` returns an empty `reply_en`.

Verified: `npx vitest run` (60/60 tests pass) and `npm run build` (tsc +
vite) both green.
