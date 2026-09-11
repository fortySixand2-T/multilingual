# QA round 056 — plan

- date: 2026-09-10
- app under test: backend + SPA single-origin at `http://127.0.0.1:9200` (all four
  levels synced: a1 409/47, a2 417/47, b1 491/46, b2 535/49)
- scope: content-only range `9cb697a..230e2f0` (PRs #92-#102) — the legacy
  lesson↔vocab coherence fix (66 lessons, 256 words) and 120 new verb entries (60
  b1 + 60 b2) with 6 new lessons in 6 new path units. No application code changed.

## Change surface (highest risk first)
Per the task brief and `git log 9cb697a..230e2f0`:

1. **120 new verbs, 6 new lessons, 6 new units** (#101 b2, #102 b1) — the single
   largest new surface this round: two brand-new deck tiles ("Verbes"/"Verbs"),
   two new unlock chains (b1.u23→u24→u25, b2.u26→u27→u28), 120 new audio clips,
   18 new hand-written exercises (9 per lesson × 6 lessons). First new path units
   since round 055.
2. **Legacy coherence fix, 66 lessons across all 4 levels** (#93 b2, #95 b1, #97
   a1, #98 a2) — ~70 hand-written mcq/word_bank/translate exercises added so every
   `new_vocab` word is actually shown. Answer keys are the risk; `match_pairs`
   exercises were script-generated from the bank (lower risk).
3. **Tooling only** (#96, #99, #100) — `check_content.py` + invariants test, two
   Claude skills. No runtime code, out of scope for testing (already ran clean —
   `a1: OK / a2: OK / b1: OK / b2: OK / cross-level: OK / content OK`).

**Already found during this planning pass (concrete leads, not just hypotheses):**
Reading the new verb lessons' `translate` exercises by hand, two `accept` lists
look like they accept a *wrong* translation, not just a lenient spelling variant:
- `content/b1/lessons/verbes-b1-01.yaml` e8: prompt "to manage to (succeed in
  doing)", answer `arriver à`, but `accept: ["arriver"]` — bare `arriver` means
  "to arrive", a different verb. Accepting it as correct for "to manage to"
  teaches the wrong translation.
- `content/b1/lessons/verbes-b1-02.yaml` e8: prompt "to complain", answer
  `se plaindre`, but `accept: ["plaindre", "se plaindre de"]` — bare `plaindre`
  (without `se`) is transitive "to pity (someone)", not "to complain". Same
  pattern.
Compare with the other four verb lessons' translate exercises, which drop only
the preposition (defensible — arguably still lenient) not the reflexive/verb
identity itself: `verbes-b2-01.e8` accepts `bénéficier`/`beneficier` for
"bénéficier de" (arguably too lenient too — the preposition is the whole
teaching point of this deck per the PR description — but at least it's still
the same verb, unlike the two b1 cases above). Testers should verify these two
concrete leads and audit the remaining `accept` lists in all 6 new lessons for
the same class of bug (accepted answer changes meaning, not just spelling).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | content/grammar | The 2 concrete leads above (`arriver`, `plaindre`) are real bugs: the `accept` list includes a translation that changes meaning, not just a spelling/preposition variant. Likely siblings across all 6 new lessons × 9 exercises = 54 exercises, and the mcq/word_bank exercises' `answer`/`explain` fields for the same 6 lessons. | Fetch or read all 6 new lesson YAMLs (`verbes-b1-01..03`, `verbes-b2-01..03`); for every `translate` exercise check whether `accept` entries preserve the verb's actual meaning (reflexive pronoun, preposition where it's the teaching point); for every `mcq`/`word_bank` verify the French is correct and `explain` justifies `answer`. Report confirmed defects + how many exercises were checked (error rate). | edge-case-breaker (curl) |
| H2 | content | New verb glosses/constructions are accurate, incl. the 4 called out in the brief (`relever de`, `se heurter à`, `tenir compte de`, `s'attendre à`) and the 7 b1 entries that intentionally duplicate an a1/a2 bare verb (`commencer_a` vs `commencer`, `essayer_de` vs `essayer`, etc.) — confirm the gloss on each duplicate pair actually differentiates the construction from the bare verb so it doesn't read as a content bug. | Fetch `/content/vocab?level=b1` and `?level=b2`, pull all `verbs`/`verbes` tagged entries, spot check every preposition-bearing headword's gloss against a dictionary, and specifically list the 7 b1 duplicate pairs with both glosses side by side to judge if it's ever confusing rather than clarifying. | edge-case-breaker (curl) |
| H3 | web/path | The 6 new units unlock strictly in order and chain from the prior last unit (`b1.u22`→`u23`→`u24`→`u25`; `b2.u25`→`u26`→`u27`→`u28`) — confirmed structurally sound by planner read of `path.yaml` diffs, and icons (`bolt`, `wave`, `chart`, `bulb`, `scale`) all map to real emoji in `Path.tsx` (no 📘 fallback) — but never seen live in a browser at the new sizes (b1 491 words/46→ wait 46 lessons unchanged count is 46 total incl. new ones, b2 49). Does the Path screen actually render/unlock them correctly for a learner progressing through, and do the new deck tiles ("Verbes" b2, "Verbs" b1) render correctly amid 491/535-word decks? | Browser: sign up fresh (or use an existing session), progress a b1 or b2 account up through the existing last unit, confirm `u23`/`u26` unlocks and not before; open Decks screen and check the new verb deck tile renders, opens, and scrolls at its size (20-60 words); open Path and scroll to confirm all new units show non-generic icons and correct titles. | absolute-beginner (browser) |
| H4 | web/vocab-deck | The 7 b1 duplicate-construction entries (bare verb already at a1/a2 + prepositional construction at b1) sit in the *same* "Verbs" deck tile — does the deck UI make the distinction legible (e.g., showing both `fr` headwords clearly), or does it read as a duplicate/confusing entry to a learner scrolling the deck? | Browser: open the b1 "Verbs" deck, scroll to a duplicate pair area if the bare verb's deck is also visible/comparable, or at minimum read each of the 7 entries as rendered and judge whether the construction is legible on its own (gloss + fr text) without needing to know it's meant to differ from a differently-tagged a1 entry. | absolute-beginner (browser) |
| H5 | content | `new_vocab` seeding for the 66 legacy-fix lessons and 6 new verb lessons actually produces SRS cards matching what's shown — spot-check that the coherence fix didn't introduce a *new* gap (e.g. `new_vocab` lists a word id that doesn't match any vocab bank entry, or an exercise references a word not in `new_vocab`), since this is exactly the bug class #93-#98 fixed for the legacy lessons and the round should confirm the fix generalizes rather than trusting `check_content.py` alone. | Read `check_content.py`'s coherence rule (does it check both directions — every `new_vocab` id shown AND every shown headword is in `new_vocab`, or just one?); independently diff `new_vocab` vs. exercise content for ~8 of the 66 fixed lessons (2 per level) plus all 6 new verb lessons; also complete one new verb lesson end-to-end in the browser and confirm its `new_vocab` words land in the Review/SRS queue. | edge-case-breaker (curl) for the diff; absolute-beginner (browser) for the end-to-end SRS check |
| H6 | content | Word_bank distractor tokens in the new/fixed exercises don't silently assemble into a second grammatically valid French sentence (the exact bug class of issue 430, already fixed once). | For all `word_bank` exercises in the 6 new verb lessons + a sample of ~10 of the 66 legacy-fix lessons (spread across levels), check whether the distractor tokens (tokens present in `tokens` but not in `answer`) could form an alternative valid sentence, or whether `answer` itself is grammatically well-formed. | edge-case-breaker (curl) |

## Coverage gaps
- No prior round has read the 6 new verb lessons' answer keys at all (this is the
  first pass).
- No prior round has looked at the ~70 legacy-coherence exercises from #93/#95/#97/#98
  individually for answer-key correctness — round 055 found the *coherence gap*
  itself (issues 754/755, now fixed); this round should sanity-check the *fix's*
  hand-written content, not re-find the same coherence gap.
- New deck tiles ("Verbes" b2, "Verbs" b1) have zero browser coverage.
- `/content/vocab/known`, `/vocab/personal*`, `/vocab/forms`, `/vocab/extra`,
  `/vocab/examples` have no issue history touching the new verb entries
  specifically (e.g. do the new prepositional headwords like `tenir compte de`
  work cleanly as personal-vocab-card keys, given issue 611's history with
  key-length limits on multi-word entries?).

## Charters (per tester, with id blocks)
- `qa-tester` (curl, persona **edge-case-breaker**, ids **800–814**): chase H1
  (verify the 2 concrete `accept`-list leads above and audit all 6 new lessons'
  answer keys for the same class of bug — report error rate), H2 (verb gloss/
  construction accuracy incl. the 7 b1 duplicate pairs), H5's data half (coherence
  diff on ~8 legacy-fix lessons + all 6 new lessons, and read whether
  `check_content.py`'s rule is bidirectional), and H6 (word_bank distractor sanity
  on the 6 new + ~10 sampled legacy-fix lessons). App base
  `http://127.0.0.1:9200`; invite token `b7XinHOMgiV_nX3j`. This is content-reading
  work — pull raw YAML/JSON and read it, don't just check status codes.
- `qa-browser-tester` (persona **absolute-beginner**, ids **815–824**): chase H3
  (Path screen unlock chain + new deck tiles at scale, all 4 icons render), H4
  (duplicate-construction legibility in the b1 "Verbs" deck), and H5's UI half
  (complete one new verb lesson end-to-end, confirm its words land in Review).
  App `http://127.0.0.1:9200`, SPA pre-built and served single-origin, sign up
  fresh with invite token `b7XinHOMgiV_nX3j` if no session exists.

## Don't re-file (already settled)
- 754 (common verbs never practiced) and 755 (lesson-vocab coherence widespread) —
  fixed by this exact round's change surface (#93/#95/#97/#98). Don't re-file the
  coherence gap itself; only file if the *fix's own content* (new exercises) has a
  fresh defect.
- 773 (review queue falsely claims all caught up) — fixed, don't re-test unless
  suspecting regression.
- 611 (personal vocab card key exceeds column limit) — known, relevant context for
  H (coverage gap on `/vocab/personal/from-word` with new long multi-word verb
  headwords like `tenir compte de`) but don't re-file the same root cause; only
  file if a *new* verb headword actually triggers it live.
- 721 (chauffeur/conducteur same gloss) — filed/settled separately, unrelated area.
- `web/e2e/specs/vocab-deck.spec.ts:30` flaky on chromium — known, re-run don't
  investigate.
- Drill / Writing grading / Speaking 503 with no provider configured — expected;
  only file if the *handling* is poor.

<!-- After the round, the planner notes each hypothesis: confirmed (→ issue NNN) /
     refuted (area sound) / untested. -->
