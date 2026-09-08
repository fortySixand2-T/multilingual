---
id: 730
title: Browsing a deck at a different level silently changes the account's active level
severity: high
area: web
persona: absolute-beginner
status: rejected
found: 2026-09-07
---

## Steps to reproduce
1. Sign up / log in, land on Home with Level pill = A1 ("Your path · A1").
2. Click the "Vocab" tile (Practice & Tools) to open the Vocabulary/Decks screen.
3. Scroll down and open any deck under a different level's heading, e.g. B2 → "Justice"
   (`/vocab/b2/justice`). Just view the first card — do not touch the "Level" dropdown
   anywhere.
4. Click "← Decks" (or navigate back to the Decks list), then click the "Vocab" tile
   again from Home (or just re-open Vocabulary).
5. Observe the "Level" pill in the top-right nav — it now reads **B2**, not A1.
6. Click "Learn" in the top nav to go Home.

## Expected
Casually browsing a vocabulary deck that belongs to a different CEFR level (which the
new 640-word/32-deck expansion makes much more inviting to do, since every level's full
deck grid is visible on one Vocabulary page) should not change the learner's actual
course level. The "Level" selector is a deliberate, explicit choice a learner makes
from the dropdown — viewing a deck card should not silently overwrite it.

## Actual
After browsing into a B2 deck and returning to the Vocabulary hub, the top-nav Level
pill flips to B2 and `localStorage.getItem('tef.level')` is now `"b2"`. Going back to
Home, the whole learning path changes: "Your path · A1" (with beginner-appropriate
"First contact" lessons like "Greetings 01") becomes "Your path · B2" showing lessons
like "Sciences B2 01". This happened with zero explicit action from the user beyond
looking at a deck — no confirmation, no toast, nothing indicating the level changed.

For an absolute-beginner persona, this is actively disorienting: they'd open the app
expecting to continue their A1 path and instead land on B2 material they can't read at
all, with no obvious explanation of why "everything changed."

## Notes
- Reproduced by viewing a B2 deck then returning to the Decks/Vocab hub — did not touch
  the Level `<select>` at any point (confirmed via `read_page`/`find` that the dropdown
  itself was never interacted with in the repro sequence).
- This looks like the Decks/Vocab screen is deriving/writing the "current level" from
  the last deck route visited (`/vocab/<level>/<theme>`) instead of treating deck
  browsing as independent of the account's selected level. Likely in
  `web/src/screens/Decks.tsx` / `Deck.tsx` or wherever `tef.level` is written.
- This bug plausibly predates this content round, but the round's own change (83 decks
  now visible across all 4 levels on one scrollable page, vs. 51 before) makes it much
  more likely a curious learner scrolls into another level's deck and trips it — so it's
  a meaningfully bigger practical risk after this expansion than before.
- Severity `high` because it silently changes core account state (course level) that
  drives Home/lesson difficulty, with no user-visible cause or way to tell what
  happened without checking devtools.

## Triage
- Explanation: Traced every write site for the `tef.level` localStorage key (`web/src/level.tsx`): (1) `LevelSwitcher`'s `<select onChange>` calling `setLevel`, and (2) `LevelProvider`'s mount-time seeding effect, which only writes `tef.level` when `localStorage.getItem(STORAGE_KEY)` is `null` (i.e. first-ever load, seeded from `me().level`). Neither `Decks.tsx` nor `Deck.tsx` reads or writes `tef.level` — `Deck.tsx` gets its level purely from the `/vocab/:level/:tag` route param (`useParams()`), scoped locally to that screen, and never touches the shared `LevelProvider` context. `App.tsx` confirms the route param and the level context are independent (`<Route path="/vocab/:level/:tag" element={<Deck />} />` inside `<LevelProvider>`, no prop/context wiring between them).
- Against spec: Unspecified directly, but the code's own design intent (comment in `level.tsx:4-6`) is explicit: level is "seeded from the learner's progress level on first load, then a manual choice sticks via localStorage" — deck browsing is not one of the two documented triggers.
- Verdict: rejected
- Rationale: Reproduced the exact steps on a clean account (signed up fresh, confirmed `tef.level` = `a1` in a freshly-cleared browser profile, clicked Vocab → opened `/vocab/b2/justice` via in-app client-side navigation → clicked "← Decks" → clicked "Learn") twice; `tef.level` stayed `a1` and Home kept showing "Your path · A1" both times — the reported flip to B2 did not occur. This matches the code trace: there is no path from viewing a deck route to writing `tef.level`. Notably, at the very start of this triage session the same shared browser profile was found to already have `tef.level = "b2"` cached from an earlier, unrelated test session — a concrete demonstration of the kind of localStorage carryover across personas/sessions in a shared browser that plausibly explains the original report (a stale value from a previous account/session, not a causal effect of browsing the B2 deck). Not re-filing this specific causal claim. Separately, `tef.level` not being namespaced per-account is a minor hygiene gap worth a lower-priority note if QA continues to reuse browser profiles across personas, but that's not what was filed here.

## Critic
- Challenge: A "you couldn't repro it, must be stale localStorage" rejection is exactly the kind of convenient explanation this role exists to distrust — it's worth independently re-tracing every write site rather than accepting the PM's story. Did the PM's own repro control for the confound it's blaming (a dirty shared profile), or just assert the explanation was plausible?
- Holds up? Yes, on independent verification, and not just on the PM's say-so. `grep -rn "tef.level\|STORAGE_KEY" web/src/` (excluding tests) shows exactly two write sites, both in `web/src/level.tsx`: the `LevelSwitcher` dropdown's `onChange`, and `LevelProvider`'s mount-time seeding effect, which only writes when the persisted key is `null`. `web/src/screens/Decks.tsx` and `web/src/screens/Deck.tsx` contain zero references to `tef.level`, `STORAGE_KEY`, or `localStorage` at all — not "no *write* path," literally no *read* path either; `Deck.tsx` gets its level purely from the `/vocab/:level/:tag` route param via `useParams()`, fully decoupled from the shared level context. No backend endpoint touched by deck browsing (`GET /content/vocab`, `/vocab/known`, personal/extra vocab routes) writes a user's `level` field either — confirmed by grep across `app/content/*.py`. Independently reproduced live in the browser on this session's own profile (already at A1, not freshly cleared): opened `/vocab` → scrolled to B2 → opened "Justice" via in-app click (not URL edit) → viewed a card, played its audio → clicked "← Decks" → clicked "Learn" — the Level pill and "Your path · A1" heading were unchanged throughout, screenshots confirm. Given zero code path exists (front or back) and live repro on a second, independently-run browser session also failed to reproduce the flip, the "stale localStorage" explanation is the only one consistent with all the evidence, not merely a convenient guess.
- Final verdict: rejected
