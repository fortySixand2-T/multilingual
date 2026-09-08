---
id: 773
title: Review queue caps at 20 cards and falsely shows "All caught up" with 180+ cards still due
severity: high
area: srs
persona: returning-learner
status: done
found: 2026-09-08
---

## Steps to reproduce
1. Sign up / log in as a B1 learner.
2. Complete a chain of lessons so that total SRS-seeding across lessons exceeds 20
   words (e.g. complete `travail-b1-01` through `immigration-b1-03`, then the new
   20-word lesson `immigration-b1-04`). `GET /srs/queue?limit=500` confirms 200 cards
   are due server-side.
3. In the browser, open **Review** (`/review`).
4. Work through all cards shown (rate each with any button — Again/Hard/Good/Easy)
   until the counter reads "20 / 20" and you submit the last rating.

## Expected
Either the Review screen keeps pulling more due cards until the queue is truly
empty (re-fetching after exhausting the first batch), or it clearly tells the
learner how many cards remain / offers a "continue reviewing" action — it should
never claim everything is done when hundreds of cards are still due.

## Actual
After rating the 20th card, the screen immediately shows the celebratory "🎉 All
caught up — No cards due right now. Finish a lesson to add new words." empty state.
At that exact moment `GET /srs/queue?limit=500` (same account) still returns **180**
due cards. The UI is lying to the learner about their review load.

Root cause (read for context, not to prescribe the fix): `web/src/api.ts`'s
`queue()` defaults to `limit=20` and matches the backend's own default
(`/srs/queue` `limit` query param defaults to 20). `Review.tsx` fetches the queue
exactly once on mount (`useEffect` with `[]` deps) and never re-queries; when
`idx >= cards.length` it renders the "All caught up" empty state unconditionally,
with no check against a true remaining-due count.

## Notes
This is exactly the SRS-flood scenario the new large lessons (up to 20 `new_vocab`
words each) create: a returning learner who does two or three new-content lessons
in a session can easily rack up 40-200+ due cards, but the app never surfaces more
than the first 20 and then tells them they're finished. As the persona (streak- and
correctness-conscious returning learner) I would trust "All caught up" and walk
away, silently leaving 90% of my due reviews undone — directly contradicting the
"due reviews wrong or empty when they shouldn't be" concern this persona cares
about. Suggest: `Review.tsx` should re-fetch `queue()` when the local batch is
exhausted (and only show "All caught up" if the fresh fetch is also empty), and/or
the empty-state copy should reflect an actual server-confirmed count of due cards
instead of just "ran out of the array we already have in memory."

## Triage
- Explanation: Confirmed exactly as described by reading the code. `web/src/api.ts`
  line 486: `queue: (limit = 20) => req<{ due: DueCard[] }>(...)`. `Review.tsx`
  fetches once on mount (`useEffect(..., [])`, line 18-20) and its empty-state
  branch (line 25-31) is `if (cards.length === 0 || idx >= cards.length)` —
  unconditional, with no re-fetch and no check of whether more cards are due
  server-side. `GET /srs/queue` itself defaults to `limit=20`
  (`app/srs/api.py` line 63). So the UI's "All caught up" is purely "I've shown
  every card in the array I fetched once," not a true empty-queue signal.
- Against spec: unspecified explicitly (no AC on review-queue pagination), but it
  contradicts the basic contract of a spaced-repetition review screen: the
  learner should be told the truth about outstanding review load, especially
  since this app's SRS docstring explicitly frames `new_vocab` seeding (up to 20
  cards per lesson) as the core mechanic — chaining a few lessons in one sitting
  (very plausible with 51 new lessons to work through) predictably produces
  40-200+ due cards, well past the hardcoded 20-card window.
- Verdict: validated
- Rationale: A returning learner (the persona who filed this, and the one this
  app's streak/XP loop is built to retain) completes their reviews, is told
  falsely that they're done, and silently abandons 90%+ of due cards with no
  visible indication anything is wrong — directly undermines the SRS retention
  loop this app is built around. High severity is warranted: it's not a display
  glitch, it's a false "you're done" signal in the app's primary retention
  mechanic. Confirmed pre-existing (not a round-055-only regression — the 20-card
  default and single-fetch pattern look original) but exposed at higher likelihood
  now that new lessons routinely seed up to 20 cards each. Straightforward fix
  per the reporter's suggestion: re-fetch `queue()` when the batch is exhausted,
  only show "All caught up" if a fresh fetch is also empty.

## Critic
- Challenge: Many spaced-repetition apps intentionally cap a review session
  (Anki's default daily review limit, for instance) so learners aren't
  overwhelmed by hundreds of due cards at once — capping at 20 and telling the
  learner "you're done for now" could be legitimate pacing UX rather than a
  bug, and the reporter/PM may be pathologizing a deliberate design choice.
- Holds up? No — this is not a designed session cap, and the challenge does
  not survive inspection. Read `web/src/screens/Review.tsx` and
  `app/srs/api.py` directly: `limit=20` is a bare function-signature default
  with no supporting concept of a "daily cap" anywhere in the code (no
  persisted per-day counter, no config flag, no distinct copy referencing a
  limit, no test asserting cap behavior — `Review.test.tsx` only covers a
  cosmetic "tough card" badge). Real capped-session designs (Anki included)
  say something like "you've reached today's review limit" and typically offer
  a way to review more if desired; this screen instead renders an
  unconditional, factually false "No cards due right now" — a `due` count of
  zero is asserted when the server-confirmed true count is 180+. There is also
  no re-fetch, no "load more," and no other screen (checked all `api.queue`
  call sites) that would give the learner an accurate picture. This is a
  single-fetch/pagination-limit artifact mistakenly presented as ground truth,
  not intentional pacing. Confirmed the root-cause mechanism exactly as
  described: `Review.tsx` fetches once on mount (`useEffect(..., [])`) and the
  empty-state branch is unconditional on `idx >= cards.length`, with
  `api.queue()` defaulting to the same `limit=20` as the backend
  (`app/srs/api.py`'s `get_queue(limit: int = 20)`). A returning learner who
  trusts the "All caught up" message and walks away silently abandons the
  large majority of their due reviews — real, high-impact, and squarely in
  this persona's stated concern (SRS reviews wrong or empty when they
  shouldn't be). Severity=high and the proposed re-fetch-before-declaring-done
  fix are both appropriate.
- Final verdict: validated

## Fix
`web/src/screens/Review.tsx`: added a second effect that fires when the local
batch is exhausted (`idx >= cards.length` and `cards.length > 0`) — it
re-fetches `api.queue()` and resets `cards`/`idx` to the fresh batch instead
of immediately rendering the empty state. The "All caught up" copy now only
renders once a fresh fetch also comes back empty (or the very first fetch was
already empty). While the re-fetch is in flight the screen shows "Checking
for more due cards…" rather than a stale or false state.
Regression tests added to `web/src/screens/Review.test.tsx`
(`describe("Review queue exhaustion (issue 773)")`): one asserts a second
`api.queue()` call happens and the next card renders (no false "All caught
up") when more cards are due after the first batch, and one asserts "All
caught up" only renders once the re-fetch itself returns empty.
`npm test` (58 passed) and `npm run build` both green.
