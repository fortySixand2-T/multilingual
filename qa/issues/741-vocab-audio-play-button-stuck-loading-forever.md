---
id: 741
title: Deck card audio "play" button gets stuck showing "…" forever after first click
severity: medium
area: web
persona: returning-learner
status: done
found: 2026-09-07
---

## Steps to reproduce
1. Sign in, go to Vocab, open any deck (reproduced on new B2 "Justice" deck and
   pre-existing A1 "Animals" deck, so not content-specific).
2. On card 1, click the normal-speed audio button (speaker icon 🔊, left of the
   turtle "slow" button).
3. Watch the button and wait 5+ seconds without clicking anything else.

## Expected
The button shows a brief loading/playing state, the clip plays, and the button
returns to the 🔊 speaker icon so the learner can tell playback finished and press
it again (or move to the next card and get a fresh 🔊 icon there).

## Actual
The button switches to a "…" (three dots) state on click and **never recovers** —
it stays "…" indefinitely (confirmed after 5+ seconds of idle waiting, and again
after navigating to a brand-new card, where the fresh card's audio button *also*
renders "…" from the very first paint, before it's even been clicked). Clicking the
stuck "…" button again does nothing visible.

Verified this isn't a backend/audio-content problem — the underlying request
succeeds fine:
```
performance.getEntriesByType('resource') for .../content/audio/b2/audio/peine.mp3
=> { duration: 12.1ms, transferSize: 5091, responseEnd: 33970 }  // fetched fast, no error

curl -H "Authorization: Bearer $TOKEN" .../content/audio/b2/audio/peine.mp3
=> HTTP 200, audio/mpeg, 4791 bytes, valid MP3 (ffprobe/file confirms)
```
So the clip loads successfully, but the button's loading-state flag is never reset
back to idle after playback — this is a frontend state bug, not a content or audio
delivery problem.

## Notes
- Reproduced on both a brand-new B2 deck (`justice`) and a long-existing A1 deck
  (`animals`), with a completely fresh page load each time (not a residual/stale
  state from earlier testing) — so this is a general Deck-screen regression/bug in
  pre-existing code, not something introduced by this round's new vocab content.
- Practical impact for a learner: after the first play on a deck, every subsequent
  card's audio button visually looks "loading" or "broken" (permanent "…"), even
  though the audio may well still be playing under the hood — there is no reliable
  visual confirmation that playback ever completes, and no way to tell a genuinely
  stuck/failed clip from a normal one.
- This materially interfered with this round's H4 audio-QA charter (verify TTS
  content quality for multi-word b1/b2 terms): the play button gives no visual
  signal of when/whether a clip finished, so a tester relying on the button's own
  state cannot distinguish "still loading," "done," or "errored."
- Likely cause (for context, not a fix instruction): whatever local state drives
  the 🔊 → "…" swap in the Deck screen's audio-button component is set on click but
  the code path that should clear it back to idle (a `.then()`/`.finally()` after
  `audio.play()`, or an `ended`/`canplaythrough` handler) isn't firing or isn't
  wired to that state.

## Triage
- Explanation: Confirmed live — signed in fresh, opened `/vocab/a1/animals`, clicked the 🔊 button on card 1 ("ours"), waited 5+ seconds: button stayed on "…" (zoomed screenshot confirms). Traced to `web/src/AudioButton.tsx`: `setLoading(true)` on click, then `await audio.play()` inside try/finally, with `setLoading(false)` in `finally`. That `finally` only runs once the `audio.play()` promise *settles* (resolves or rejects) — and per a direct in-page repro (`new Audio(url); audio.play()` raced against a 5s timeout), the promise neither resolved nor rejected within 5 seconds on this content (a valid, freshly-fetched 5.4KB `audio/mpeg` blob — not a corrupt-file issue). With no timeout/fallback path in `AudioButton`, `loading` has no way back to `false` once `play()` hangs, so the button is stuck on "…" indefinitely with no way to tell a stuck clip from one that's still loading. Separately, `VocabWord.tsx` renders `<AudioButton audioKey={card.audio} .../>` with no `key` prop tied to `card.id`, so React reuses the same component instance (and its `loading` state) across cards — this explains the reporter's second observation that a brand-new card's button renders "…" from first paint, before any click on that card, once a previous card's click got stuck.
- Against spec: Unspecified — no explicit UX requirement for audio-button state recovery in the technical plan, but it's a basic expectation of any async-loading UI affordance (a busy indicator that can never resolve is a functional regression regardless of spec text).
- Verdict: validated
- Rationale: Reproduced on both a new B2 deck and a pre-existing A1 deck with a fresh page load, confirming it's a general Deck-screen bug, not content-specific — consistent with the reporter's own framing as pre-existing code newly exercised at this round's scale, not a regression from the content commit. Two compounding real defects: (1) no timeout guard around `audio.play()` leaves the button unrecoverable whenever the play promise doesn't settle, and (2) the missing `key` on `AudioButton` means the stuck state bleeds into every subsequent card. Together these directly undermined this round's own H4 audio-QA charter (verifying TTS content quality), matching the tester's stated impact. `medium` severity is reasonable as filed — it's a real, reproducible frontend defect blocking a specific but non-critical workflow (audio verification), not blocking the primary vocab browse/SRS flow.

## Critic
- Challenge: A `disabled` button stuck showing "…" is a cosmetic detail that could look far worse in a code diff than it plays on screen — is this actually a functional block for a learner, or just a slightly wrong icon after audio has already played? If the clip fires and is audible regardless of button state, a learner arguably doesn't care that the button never resets.
- Holds up? Yes — drove it live rather than trusting the report. Signed into a running session already on Home/A1, navigated Vocab → B2 "Justice" deck via in-app clicks, clicked the 🔊 button on card 1 ("récidive"), waited 5s: screenshot confirms the button is stuck on "…" and (per the code trace, `disabled={loading}`) is now unclickable — this is not just a stale icon, the button is functionally dead until the learner navigates away, matching the reporter's own note that clicking the stuck button "does nothing visible." This is a real, visible defect for exactly the workflow (listening to new pronunciation clips) this content-heavy round is meant to exercise. The severity ceiling is still appropriately capped at `medium` — it doesn't block browsing, flipping, or "add to review," and the SRS/browse flows this round cares about most (H6/H7 in the round plan) are unaffected — but it is a genuine, reproducible frontend regression, not a theoretical or self-inflicted one, so validated stands.
- Final verdict: validated

## Fix
Fix: `web/src/AudioButton.tsx` now races `audio.play()` against a 4s timeout
(`Promise.race`) so the `finally` clearing `loading` always runs even if
`play()` never settles. `web/src/VocabWord.tsx` now passes `key={card.id}`
(and `${card.id}-m` / `${card.id}-f` for dual-gender cards) to `AudioButton`,
so React remounts a fresh instance per card instead of reusing a stuck
`loading` state across cards. Regression test added in
`web/src/AudioButton.test.tsx` (mocks a `play()` that never resolves, asserts
the button recovers after the fallback timeout); full frontend suite green
(56 passed) and `npm run build` succeeds.
