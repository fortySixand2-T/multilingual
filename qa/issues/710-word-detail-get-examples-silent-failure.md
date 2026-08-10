---
id: 710
title: "Get examples" button in Forms & examples panel gives zero feedback on failure (Deck.tsx & MyDeck.tsx)
severity: medium
area: web
persona: absolute-beginner
status: done
found: 2026-08-09
---

## Steps to reproduce
1. Sign up / log in (invite code `friend-001`).
2. Go to Vocab (content-bank deck), open any A1 theme (e.g. "Family"), flip a card
   to reveal the meaning (e.g. "grand-mère" → "grandmother").
3. Click the collapsed "Forms & examples ▸" panel to expand it. It loads and shows
   "FORMS: No forms for this word." and "EXAMPLES: Press for a sentence using this
   word." with a "✨Get examples" button — this part degrades gracefully.
4. Click "✨Get examples".
5. Observe the panel: nothing changes. No spinner appears, the button stays exactly
   as it was, and the "Press for a sentence using this word." placeholder text is
   never replaced by anything (no sentence, no error, no retry hint).
6. Checked the network tab: the click does fire `POST /vocab/examples`, which
   returns `503` (expected here — no LLM provider configured). The console shows
   no JS errors.
7. Reproduced identically on the personal "My deck" screen: added personal cards
   directly via `POST /vocab/personal` (`chat`/noun and `vite`/adverb, since the UI's
   own add-word flow also needs the LLM and 503s with a proper error banner —
   that part is fine and out of scope). Expanding either personal card's panel and
   clicking "✨Get examples" produces the exact same result: the button click does
   nothing visible, the 503 is swallowed silently.

## Expected
On a failed "Get examples" request the UI should show *some* feedback — e.g. a
brief error message near the button ("Couldn't generate an example right now"), a
disabled/loading state while the request is in flight, or reverting cleanly with a
retry affordance. This matches how the sibling "FORMS" section already degrades
(it renders "No forms for this word." when generation isn't available) and how the
personal-deck word-add flow degrades (it shows "Error: The AI service is
temporarily unavailable. Please try again shortly."). The "Get examples" flow
should be at least as good.

## Actual
Clicking "✨Get examples" is a total no-op from the learner's point of view: no
loading indicator, no error text, no console error — the button and the "Press for
a sentence using this word." placeholder are pixel-identical before and after the
click, even though the network request did fire and did fail with a 503. An
absolute-beginner persona would very plausibly conclude the button is broken and
give up, or tap it repeatedly.

## Notes
- Reproduced on both `Deck.tsx` (content-bank shared vocab, e.g.
  `/vocab/a1/family` and `/vocab/a1/colours`) and `MyDeck.tsx` (personal deck,
  `/my-deck`) — same underlying `WordDetail.tsx` component and same
  `POST /vocab/examples` endpoint, so likely a single shared fix.
- Contrast with the "FORMS" half of the same panel: a failed `POST /vocab/forms`
  (also 503 here) *does* result in a clear "No forms for this word." message, so
  the component clearly has a pattern for rendering a fallback state on failure —
  it's just not applied to the "Get examples" button/click handler.
- Not filing the LLM 503 itself — that's the expected no-ollama environment
  limitation. Filing only the missing failure-state UI around this one specific
  action.

## Triage
- Explanation: In `web/src/screens/WordDetail.tsx`, `newExample()` (the "✨ Get
  examples" handler, lines 45-54) sets `exState` to `"loading"`, awaits
  `api.vocabExamples(cardKey)` (`POST /vocab/examples`), and on failure its `catch`
  block does only `setExState("idle")` — it never sets any error/message state, and
  `examples` is untouched (stays `[]`). Since the render logic at line 97
  (`examples.length === 0 && exState === "idle"`) is the same condition true both
  before and after a failed click, the UI reverts to a pixel-identical state: same
  placeholder text ("Press for a sentence using this word."), same button label
  ("✨ Get examples"), no error, no console log. This is a genuine bug in the catch
  branch, not a misreading of async timing — reproduced by direct code trace and
  matches the tester's captured network/console evidence exactly (503 fires, no JS
  error, DOM unchanged).
  Contrast confirms the component *has* the pattern to do this right: the sibling
  `expand()`/forms path (lines 20-43) has a dedicated `formsState` enum including
  `"none"`, and its `catch` sets `formsState("none")` which renders "No forms for
  this word." (line 73) — a real fallback message. `exState`, by comparison, only has
  `"idle" | "loading" | "over_budget"`; there is no `"error"`/`"none"` member and
  no corresponding render branch, so the catch has nowhere to route the failure to.
- Against spec: `TEF_Platform_Technical_Plan.md` AC1.5 requires budget-exceeded to
  "return a graceful message" (implemented here as `over_budget`), establishing the
  house rule that LLM-adjacent failures need learner-visible handling, not silence.
  `qa/README.md`'s Scope note is explicit: the 503 itself is expected/out of scope
  in this no-provider environment, but testers are directed to file cases where "the
  *handling* is poor" — which is precisely this case.
- Verdict: validated
- Rationale: An absolute-beginner persona clicking "✨ Get examples" gets zero
  signal that anything happened — no spinner, no error, no retry hint — indistinguishable
  from a dead/broken button, which plausibly causes them to give up or repeat-click.
  The fix is small and localized: extend `exState` with an `"error"` (or reuse a
  `"none"`-style) variant and render a short message in the catch branch, mirroring
  the existing Forms fallback pattern already in the same component.

## Critic
- Challenge: The strongest case for no change: this only manifests when
  `POST /vocab/examples` fails, and in this environment that's exclusively because
  no ollama provider is configured — a test-rig artifact, not something a deployed
  learner hits under normal conditions. One could argue this is "working as designed"
  (idle state before any generation looks the same as idle state after a failed one),
  and that adding a new `exState` member is unwarranted churn for a corner case that's
  rare in production (LLM providers are usually up).
- Holds up? No. Re-read `web/src/screens/WordDetail.tsx` directly (lines 45-54) and
  reproduced live in Chrome on `/my-deck`: clicked "✨ Get examples" on the "chat"
  card and the DOM is byte-for-byte unchanged before/after — confirms the PM's trace
  exactly, this isn't a misreading of async timing. The "only happens with no LLM
  provider" framing doesn't hold: the bare `catch { setExState("idle") }` swallows
  *any* failure of `api.vocabExamples` — network blips, provider rate-limiting,
  timeouts, transient 5xx — none of which require tampering or an artificial
  environment; they're ordinary production failure modes for an LLM-backed feature.
  It's also not "working as designed": the sibling Forms path in the same file
  already has a `formsState` enum with a `"none"` member and a matching render
  branch specifically to avoid this silent-failure shape, so the design intent is
  clearly to surface failures, and Examples just missed getting the same treatment.
  Impact is real, not cosmetic — a beginner has no way to distinguish "still
  loading," "broken," and "failed, please retry," which is exactly the kind of
  confusion `TEF_Platform_Technical_Plan.md` AC1.5 is trying to prevent for
  LLM-adjacent failures. The fix (one enum member + one render branch) is strictly
  smaller than the sibling Forms handling already merged in this file, so it isn't
  disproportionate complexity for the payoff.
- Final verdict: validated

## Resolution
- Status: done
- Fix: `web/src/screens/WordDetail.tsx` — added an `"error"` member to the
  `exState` union (`"idle" | "loading" | "over_budget" | "error"`), and the
  `catch` block in `newExample()` now sets `exState("error")` instead of
  silently falling back to `"idle"`. Added a matching render branch — "Couldn't
  generate an example right now." — right below the existing `over_budget`
  message, mirroring the sibling Forms `"none"` fallback pattern already in the
  same component. Also tightened the placeholder/list rendering so the "Press
  for a sentence…" placeholder only shows in the true untouched `"idle"` state
  (not alongside the new error message), and the example list only renders
  when `examples.length > 0` (previously an `else` branch that could render an
  empty `<ol>`).
- Tests added: `web/src/screens/WordDetail.test.tsx` — new case "shows an error
  message when the examples request fails (e.g. 503)", which mocks
  `api.vocabExamples` to reject and asserts the new error text appears and the
  stale "Press for a sentence…" placeholder does not silently reappear.
- Verified: `cd web && VITE_API_BASE="" npm run build` — clean.
  `npx vitest run` — 48 passed (14 files), including the new WordDetail case.
  Backend untouched (frontend-only fix), no backend tests run.
