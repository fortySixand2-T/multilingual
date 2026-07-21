# QA round 040 — plan

- date: 2026-07-20
- app under test: single-origin API + built SPA on :8123 (branch `qa/grammar-round` =
  `feat/grammar-categories` + QA-agent tooling)
- scope: grammar reference category grouping/filter/search slice (`web/src/screens/Grammar.tsx`,
  `app/content/models.py` GRAMMAR_CATEGORIES, `GET /content/grammar`) — UI-focused, targeted.

## Change surface (highest risk first)

Two commits on top of the merged `feat: grammar reference index` baseline:

1. `9b08d99 feat(grammar): categorize grammar points into 8 grammatical families` — adds
   `GRAMMAR_CATEGORIES` (8-value controlled set) + validated `grammar_category` on `Lesson`;
   tags all 132 lessons a1–b2; endpoint emits `grammar_category`; `Grammar.tsx` rewritten to
   group by category (was by unit/theme) with filter chips + search.
2. `5e5bb38 test(grammar): cover category grouping + fix latent duplicate "Other" bucket` —
   a **prior by-hand QA pass already caught and fixed one bug**: `Grammar.tsx` iterated
   `[...categories, OTHER]` while `categories` already appended `OTHER`, producing a duplicate
   group with a duplicate React key. Fixed to iterate `categories` directly, and added
   `Grammar.test.tsx` (3 tests: canonical grouping + Other-bucket, single-chip filter,
   search-composes-with-filter).

So the obvious first-order bugs are already fixed and covered by unit tests. This round should
target what the *unit tests don't cover* — real-browser rendering/interaction across all 4
levels, chip toggle-off, "All" reset, level-switch state, and visual layout at the live category
counts — plus a scan for gaps the existing test double didn't exercise (search doesn't reset on
level switch is a candidate, see H4).

Live category distribution per level (checked directly against the running server, not the
mocked b2-only unit test fixture):
- a1: 36 items / 4 categories (Expressions & communication 27, Articles & determiners 5,
  Adjectives & comparison 3, Verb conjugation & tenses 1) — no "Other".
- a2: 36 items / 3 categories (Expressions & communication 28, Verb conjugation & tenses 5,
  Adjectives & comparison 3) — no "Other".
- b1: 30 items / 5 categories (Expressions & communication 12, Verb conjugation & tenses 7,
  Adjectives & comparison 4, Pronouns 4, Subjunctive 3) — no "Other".
- b2: 30 items / 6 categories (Logical connectors 8, Sentence structures 8, Subjunctive 6,
  Verb conjugation & tenses 4, Pronouns 3, Adjectives & comparison 1) — no "Other". With the
  "All" chip that's **7 chips on one row** — the densest chip row, and the one most likely to
  wrap/overflow on a narrow viewport.

No level currently has an uncategorized (empty `grammar_category`) lesson, so the "Other"
bucket is untestable against live data (only the unit test's synthetic fixture exercises it) —
note this as a coverage gap, don't force it in the browser round.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | web/interaction | Clicking the active chip again does not toggle it off (`setCat` uses a toggle, but nothing exercises this in the unit tests) — user gets stuck filtered with no visible way to clear except "All" | click a chip to filter, click the *same* chip again, expect it un-filters back to all groups for that level | edge-case-breaker |
| H2 | web/interaction | "All" chip does not fully reset an active category + search combo, or leaves stale visual state (chip still highlighted) | select a category, type a search term, click "All", expect all groups return and no chip stays visually active except "All" | edge-case-breaker |
| H3 | web/visual | b2's 7-chip row (6 categories + All) wraps awkwardly, overlaps, or causes horizontal scroll/clipping at common viewport widths | load `/grammar` on b2, inspect the chip row at desktop and a narrow/mobile width, screenshot | returning-learner |
| H4 | web/state | Search text is **not cleared** on level switch (`useEffect` resets `items`/`error`/`cat` but not `q`) — switching from a level where the query matched something to one where it doesn't silently shows "No grammar points match your filter" with no visible reason | on b2, type a search term that matches (e.g. "subjonctif"), switch level to a1 (no Subjunctive category, term won't match), observe whether the search box still shows the old text and whether the empty-state message explains why | edge-case-breaker |
| H5 | web/rendering | Category grouping order matches canonical `GRAMMAR_CATEGORIES` order (not alphabetical, not first-seen) across a1/a2/b1/b2, each with a different subset present | load `/grammar` per level, read off group headers top-to-bottom, compare to canonical order minus absent categories | returning-learner |
| H6 | web/flow | Tapping a grammar point navigates to the *correct* lesson (lesson_id in the entry matches the lesson opened), and the back-arrow/nav returns cleanly to the grammar list with prior filter state (or a clean reset — either is fine, but confirm it's not broken/blank) | click a grammar entry, confirm the lesson screen matches (title/unit consistent with what was shown), navigate back | returning-learner |
| H7 | web/a11y | Chips and the search input have real accessible names/roles (not just visual styling) — chip buttons keyboard-focusable and screen-reader-labelled by their category text, not by an emoji or icon alone | tab through the chip row and search input, inspect accessible name/role, check for console errors on load/interact | edge-case-breaker |
| H8 | web/content | Category filter + search combined can produce a confusing zero-result state that looks identical to "not loaded yet" or a real error, with no way to tell what's filtered | craft a search+chip combo that matches nothing, confirm the empty-state message is present and distinguishable from the loading/error states | edge-case-breaker |
| H9 | content/data | Duplicate `grammar_point` labels (issue 446, deferred, e.g. A1 "cardinal numbers" ×2) may now land in the *same category* group, compounding the ambiguity the deferred issue already flagged — worth a quick visual check but **do not re-file 446 itself** | on a1, find numbers-01/numbers-02 in the rendered list, check whether they land in the same category group and whether that makes them harder to tell apart than before | returning-learner |

## Coverage gaps
- No lesson currently has an empty `grammar_category` live, so the "Other" bucket path is
  only covered by the unit test's synthetic data — not observable in the real browser this
  round. Note as untested, not a defect.
- `GET /content/grammar` HTTP-level behavior (auth, level validation, field shape) was already
  covered in a prior round (issues 443–446) and is unchanged by this slice — out of scope,
  no curl-level tester needed this round.
- a2 (3 categories, no Subjunctive/Pronouns/etc.) and b1 (5 categories) are the least-tested
  category counts — most prior by-hand QA focused on b2. Worth at least a glance.

## Charters (per tester, with id blocks)

- `qa-browser-tester` as **returning-learner** (ids 040–049): calm-path browse across levels.
  Chase H3 (b2 chip row visual/wrap check), H5 (canonical grouping order, spot-check a1/a2/b1/b2),
  H6 (tap-through to correct lesson + back nav), H9 (duplicate-label same-category check on a1,
  informational only — do not re-file 446). Sign in via the provided signup+localStorage
  injection steps; set `tef.level` to each of a1/a2/b1/b2 in turn to compare.

- `qa-browser-tester` as **edge-case-breaker** (ids 050–059): adversarial interaction probing.
  Chase H1 (chip toggle-off), H2 ("All" reset with active chip+search), H4 (search persistence
  across level switch — the most likely real bug in this slice), H7 (a11y/keyboard/console
  errors), H8 (zero-result empty state clarity vs loading/error states).

Both testers: use the running app at **http://127.0.0.1:8123** (not 9000). Mint a token via
`POST /auth/signup` with a fresh email + invite code `friend-001` or `friend-002`, inject
`tef_token` and `tef.level` into `localStorage`, then navigate to `/grammar`. Only test this
screen and its direct navigation target (the lesson screen reached by tapping an entry) — do
not wander into unrelated app areas (drills, mocks, group board, etc.).

## Don't re-file (already settled)
- 443 — A1 grammar index missing lessons (stale DB) — done, fixed via content-sync; not
  reproducible now (live DB confirmed to return full counts above).
- 444 — grammar endpoint 401 test coverage — rejected (project convention, no defect).
- 445 — grammar test count assertion — done, fixed.
- 446 — duplicate grammar_point labels (numbers/shopping/weather, A1/A2) — **deferred**
  (content-authoring issue, out of scope for this code slice). H9 above is a *look*, not a
  re-file — if it's materially worse under category grouping (e.g. now visually adjacent in
  the same small group with no other distinguishing text), a *new*, narrowly-scoped issue
  about the category-grouping compounding effect could be justified, but do not just refile 446.
- The `[...categories, OTHER]` duplicate-group/duplicate-key bug — already found and fixed in
  `5e5bb38` on this branch, and locked by `Grammar.test.tsx`'s first test. Don't re-file; do
  feel free to re-verify it stays fixed if you happen to hit an uncategorized lesson.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
