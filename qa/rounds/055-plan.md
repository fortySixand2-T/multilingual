# QA round 055 — plan

- date: 2026-09-08
- app under test: backend + SPA single-origin at `http://127.0.0.1:9200` (built with
  `VITE_API_BASE=""`, all four levels synced)
- scope: the whole vocabulary + learn-path arc merged to `main`, `77dbcd0..328644b`
  (PRs #84–#90) — 640 new words + 279 deepened words (bank → 1732), the #85 SPA
  routing fix, and 51 new lessons in 47 new units that bring every level to 100%
  taught coverage (a1 409/409, a2 417/417, b1 431/431, b2 475/475; 91 units total).

## Change surface (highest risk first)
Per commit, in the order they landed:
- `21042c3` (#84) — 32 new vocab decks, 640 words. **Already thoroughly audited by
  round 054** (all genders cross-checked, glosses spot-read, decks-screen scale
  tested). Treat vocabulary *entries* from this commit as settled; don't re-audit.
- `572d4de` (#85, folded into the arc) — SPA catch-all serves the app shell for
  routes colliding with API prefixes (`/vocab`, `/comprehension`, `/exam`). Verified
  by the requester with curl only — **never exercised in a real browser** (an actual
  page refresh does more than curl: it re-triggers asset loading, React Router
  mount, and any client-side redirect logic).
- `eba6fb9` (#86) — deepened 16 decks, +279 words, bank 1453 → 1732. Requester
  cross-checked 196/279 nouns against `fr_gender.tsv`; the other ~83, plus every
  gloss and CEFR placement in this slice, are **unaudited by anyone but the author**.
- `572d4de/ce07a23/04f5a9e/328644b` (#87–#90) — 51 new lessons across 47 new units
  (a1 +9 units, a2 +11, b1 +12, b2 +15). Hand-authored answer keys throughout
  (mcq/translate/word_bank/listen_type). **The single highest-risk surface this
  round**: a wrong key actively teaches false grammar. Also new: `Path.tsx` icon
  mapping (37 names → emoji, previously only 2 mapped) and larger unlock chains.

**Already found during this planning pass (concrete lead, not just a hypothesis):**
reading `content/b2/lessons/psychologie-b2-01.yaml` and `justice-b2-01.yaml` by hand,
`new_vocab` lists 20 word ids each, but the `match_pairs`/`translate` exercises only
ever *show* 15/20 (psychologie: `psychologue`, `émotion`, `perception`, `conscience`,
`adaptation` never appear in any exercise) and 18/20 (justice: `poursuite`,
`légitimité` never appear) respectively. So a lesson can seed SRS cards for words the
learner was never shown or drilled on — this is exactly the "softer dishonesty"
pattern called out below (§3), and it's already confirmed in 2/51 lessons sampled.
Testers should quantify how widespread this is, not just re-find these two.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | content/grammar | Hand-written answer keys in the 51 new lessons contain errors: `translate` `accept` lists too narrow/broad, `word_bank` distractor tokens that assemble into a second valid sentence, `mcq` options with >1 defensible answer, wrong gender/agreement claims in `explain` text. Grammar keys are the specific failure class prior rounds (issue 430) have already caught once in older content. | Prioritize the grammar-heavy set: `psychologie-b2-01` (subjunctive), `justice-b2-01` (passive), `politique-b2-04` / `environnement-b2-04` (si clauses), `adjectives-01` (agreement), `countries-01` (en/au/aux). Then sample ~10 more lessons spread across all 4 levels and grammar categories. For each exercise checked, verify the French is correct AND the `explain` actually justifies the `answer`. Report an **error rate** (defects / exercises checked), not just defects. | edge-case-breaker (curl) |
| H2 | content | The #86 deepening slice's 279 words were never independently audited for gender/gloss/CEFR fit — 196/279 nouns were cross-checked by the author against `fr_gender.tsv`, the rest (~83) plus all glosses/placements were not. | Fetch `/content/vocab` for the deepened decks (`b1: immigration, travail, logement, argent, health`; `b2: travail, politique, economie, societe, environnement, sante`; `a2: travail, sante, transport`; `a1: verbs, adjectives`) and independently verify a broad sample of genders/glosses, weighting toward abstract B1/B2 terms where gloss ambiguity is likelier than in A1 concrete nouns. | edge-case-breaker (curl) |
| H3 | content | Lesson↔vocab coherence: a lesson's `new_vocab` (which drives SRS seeding, up to 20 cards) doesn't match what its exercises actually teach/practice — confirmed present in 2/2 lessons spot-read this pass (see above). | Systematically diff `new_vocab` ids against every French headword that appears in that lesson's exercises, across a sample of ~15–20 lessons spread over all 4 levels (not just the 2 already found). Report the coverage rate and file the worst offenders (biggest gap, or vocab CEFR-inappropriate for what's shown). | edge-case-breaker (curl) |
| H4 | web/SRS | Completing a new lesson can seed up to 20 SRS cards at once (existing lessons seeded 2–8) — does the review queue stay usable (readable count, no pagination break, no crash) after finishing 2+ new lessons back to back? | Sign up fresh, complete two new lessons from different decks/levels, then open Review and assess: is the queue navigable, does count/UI make sense, can cards be flipped/marked without issue? | returning-learner (browser) |
| H5 | web/path | 91 units across 4 levels (21–25 per level) with unlock chains — does the Path screen render acceptably at this scale (no overflow/wrapping breakage), and do the chains actually gate correctly (e.g. a1.u21 locked until a1.u20/earlier prerequisite is done; no orphaned or unreachable unit)? | Browser: open Path for a1 (21 units) and one deeper level, scroll through, confirm locked/unlocked states look right and match actual completion state; also fetch `/content/path` and check for any unit whose `requires`/prerequisite id doesn't exist in the level, or any unit unreachable by chain from u1. | absolute-beginner (browser) + edge-case-breaker (curl, structural check) |
| H6 | web/routing | The #85 fix was verified with curl only — does an actual browser refresh on `/vocab`, `/comprehension`, `/exam` (and a deep sub-path like `/vocab/deck/<id>` if it exists) correctly load the app shell and not a raw 404 or blank page? | Browser: navigate into the app normally to reach each of these routes, then hard-refresh the tab (not just client-side nav) and confirm the SPA still renders, not an error page. | absolute-beginner (browser) |
| H7 | web/path | Unit icons (37 names mapped to emoji in `Path.tsx`) — do any of the 91 units still render the generic 📘 fallback, and are the chosen emoji sensible for their theme (not just "not broken")? | Browser: scroll all 4 levels' Path screens, note any unit showing 📘 or a clearly mismatched icon. | absolute-beginner (browser) |
| H8 | web/flow | End-to-end: start a new lesson (from #87–#90), complete it, and confirm its `new_vocab` words actually arrive in the Review queue and can be reviewed — the full loop this whole arc exists to serve. | Browser: pick one new lesson each from two different levels, complete it (submit realistic answers), then check Review for the new cards. | absolute-beginner + returning-learner (browser) |

## Coverage gaps
- No prior round has read any of the 51 new lessons' answer keys — this is the first
  pass over that content at all (round 054 scoped out lessons entirely).
- No issue history touches `/content/path` structural integrity (prerequisite graph)
  at 91-unit scale — only ever exercised at ~44 units pre-arc.
- Path.tsx icon mapping is new code, zero browser coverage yet.
- The #86 deepening slice's glosses/CEFR placement have zero independent review.

## Charters (per tester, with id blocks)
- `qa-tester` (curl, persona **edge-case-breaker**, ids **750–761**): chase H1
  (grammar-heavy sample list above + ~10 more spread across levels/categories —
  report an error rate), H2 (deepened-deck gender/gloss spot-check, weight toward
  B1/B2 abstract terms), H3 (lesson↔vocab coherence diff across ~15–20 lessons,
  quantify coverage rate; the two already-found gaps above don't need re-filing as
  new leads — extend the sample past them), and H5's structural half (`/content/path`
  prerequisite-graph sanity check for orphans/dangling refs). App base
  `http://127.0.0.1:9200`; invite codes `friend-001`–`friend-003` available. This is
  content-reading work — pull the raw YAML/JSON and read it, don't just check status
  codes.
- `qa-browser-tester` (persona **absolute-beginner**, ids **762–772**): chase H5's UX
  half (Path screen render + visual unlock-state sanity at a1/a2 scale), H6 (hard
  refresh on `/vocab`, `/comprehension`, `/exam`), H7 (icon scan across all 4 levels'
  Path screens), H8 for an a1 or a2 lesson (complete it, confirm words land in
  Review). App `http://127.0.0.1:9200`, SPA pre-built and served single-origin. Sign
  up fresh with `friend-004` if no session exists.
- `qa-browser-tester` (persona **returning-learner**, ids **773–783**): chase H4 (SRS
  flood — complete two new lessons from different decks, assess Review queue
  usability after), H8 for a b1 or b2 lesson, and a second independent pass at H6 on
  a level-appropriate deep link (confirm the routing fix isn't level- or
  session-state-dependent). App `http://127.0.0.1:9200`. Sign up fresh with
  `friend-005` if no session exists.

## Don't re-file (already settled)
- Anything about the 640 words / 32 decks from #84 (gender, gloss, register, audio,
  Decks-screen scale, epicene handling) — exhaustively covered by round 054. Only
  file if you find something round 054's issues (720, 721, 730, 740, 741) don't
  already describe.
- 720 epicene badge, 741 stuck audio button — fixed. Don't re-test unless you suspect
  a regression.
- `web/src/VocabWord.tsx` `EPICENE_IDS` hardcoding 8 word ids — known design debt,
  not a new bug. Only file if you find a concrete user-visible bug beyond "won't
  cover future epicene words."
- `web/e2e/specs/vocab-deck.spec.ts:30` flaky on chromium — known, re-run don't
  investigate.
- 430 (`ville-b2-01.e4` word_bank truncated grammar) — already fixed; don't re-file
  the same pattern there, but the same *class* of bug (word_bank distractor forms a
  second valid sentence) is explicitly in scope for H1 in the new lessons.
- 721 (`chauffeur`/`conducteur` same gloss "driver") — filed, not yet triaged as of
  this plan; don't re-file the same pair.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
