# QA round 059 — plan

- date: 2026-10-25
- app under test: backend + SPA single-origin at `http://127.0.0.1:9200` (worktree
  `delf-tef-mocks-latency`, branch `qa/059-content-quality-fixes`, `origin/main` at
  686cebd), pointed at the box's real Ollama (`OLLAMA_BASE_URL=http://10.0.0.54:11434`,
  `AI_ROUTING_PATH=app/config/ai_routing.ollama.yaml`,
  `OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M`). Scratch DB `/tmp/qa059/qa.db`, content +
  writing tasks synced (`python -m app.content.sync <lvl>` and
  `python -m app.assessment.sync <lvl> content` for a1/a2/b1/b2). `STT_BACKEND`/
  `TTS_BACKEND=disabled` (no Piper locally — this round's IPA hypotheses target
  exactly the no-TTS code path, so that's the right environment, not a gap).
- scope: PR #121 (686cebd, squash-merged, now the tip of `origin/main`) — the fixes
  for QA issues **830** (`/vocab/forms` rule-based agreement/elision, `app/content/
  forms.py`), **831** (writing grader drops uncited corrections, `app/assessment/
  grader.py` + `writing_grader.md`), **832** (LLM no longer supplies IPA; Piper-only,
  filled on first voicing, `app/content/enrich.py`/`lookup.py`/`personal_api.py`).
  This round tests the *fixes themselves* for new edge cases/regressions they
  introduce — not a re-litigation of 830/831/832, which are closed `fixed`.

## Change surface (highest risk first)

1. **`app/content/forms.py` `tidy_forms`/`_verb_form`/`_adjective_forms`/
   `_adjective_plural`** — brand-new rule engine (no prior behavior to regress
   against, but plenty of French-grammar edge cases a generic rule set can miss).
   Applied both on generation (`generate_forms`) AND on every read of previously
   stored forms (`vocab_extra_api._stored_forms`) — a rule bug here doesn't just
   affect new cards, it silently rewrites what's already stored every time a user
   reopens the study panel.
2. **`app/assessment/grader.py` `_is_genuine`/`parse_feedback`** — a correction now
   survives only if `reference` is in the 8-key `GRAMMAR_REFERENCES` set AND
   `correction != excerpt`. This fixed issue 831's over-triggering (false
   positives) but is a blunt filter that can equally suppress genuine errors whose
   correct tag isn't in the list (there is, notably, **no vocabulary/word-choice
   key** — `vocabulary` is a *scored criterion* but not a citable `reference`) —
   trading false positives for false negatives is the obvious risk of this shape
   of fix.
3. **`app/content/enrich.py`/`lookup.py`/`personal_api.py` IPA removal** — IPA is
   now Piper-only, filled lazily. Two asymmetric code paths worth distinguishing:
   `lookup.fresh_lookup` (shared dictionary cache, `vocab_lookup` table) sets
   `row.ipa = ipa[:64]` unconditionally when `tts is not None`; `personal_api.
   _serve_audio` (personal `user_vocab` cards) sets `row.ipa = row.ipa or ipa[:64]`
   — only fills if currently *falsy*. That `or` guard means a personal card that
   already has a **stale, wrong, pre-fix LLM-guessed IPA** (any card added before
   this PR shipped, under the old code that stored `ipa="hɒrəbəl"` straight from
   the model) will **never** be corrected by a later voicing, because the row's
   `ipa` field is truthy already. This is the one piece of this PR's diff that
   isn't purely additive — it's a potential permanent-staleness bug on existing
   data, worth checking directly before trusting the "filled on first voicing"
   framing in the PR description.

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | content/forms | Reflexive verbs (`s'amuser`, `se lever`, …) lose the subject pronoun entirely when the model drops it, because `_verb_form`'s "model often drops the pronoun, prepend 'je'" rescue is gated off whenever `lemma.startswith(("se ", "s'"))` — so a model reply of bare `"me lève"` (no `je`) is left as `"me lève"` with no subject at all, never becoming `"je me lève"`. (The one existing reflexive test seeds a reply that *already* starts with `"je "`, so this gap is untested.) | `POST /vocab/personal/from-word {"word":"se lever"}` (and `s'amuser`, `se souvenir`), then `POST /vocab/forms` a few times (temp 0 so should be deterministic, but sample 3-5x); read the `présent`/`passé composé`/etc. `fr` values — flag any missing a leading subject pronoun (`je`, `tu`, `il`…). | edge-case-breaker |
| H2 | content/forms | Impersonal verbs (`pleuvoir`, `falloir`, `neiger`) get a **wrongly-prepended "je"** when the model correctly omits a subject or uses "il" in a form `_SUBJECT` doesn't match — `_verb_form` only skips the "je" rescue for reflexives, not impersonals, so e.g. a bare `"pleut"` reply becomes `"je pleut"` (ungrammatical: impersonal verbs only take "il"). | `POST /vocab/personal/from-word {"word":"pleuvoir"}` and `falloir`, then `/vocab/forms`; check every form starts with "il " (or is correctly impersonal) and never got rewritten to start with "je". | edge-case-breaker |
| H3 | content/forms | Invariable/irregular-plural adjectives (`marron`, `chic`, `sympa`, `super`) get a rule-generated "-s" plural from `_adjective_plural` that's wrong for words that don't take one in standard usage (`marron` stays `marron` as a color adjective), and irregular masculine-before-vowel forms (`beau`→`bel`, `nouveau`→`nouvel`, `vieux`→`vieil`) are never produced since `_adjective_forms` always uses the bare lemma as masculine with no special-case. | `/vocab/personal/from-word` + `/vocab/forms` for `marron`, `chic`, `beau`, `nouveau`, `vieux`; read all 4 adjective-form rows for each. | edge-case-breaker |
| H4 | content/forms | `tidy_forms`'s non-Latin-script filter (`ord(c) < 0x250`) is applied on **every read** of stored forms, not just generation — confirm a previously-stored, already-correct forms row is unaffected by a second/third read (idempotence across the *read* path specifically, not just the generation path the existing test covers), and that a stored row containing a legitimate character ≥ U+0250 (e.g. a rare IPA-adjacent loanword) isn't silently dropped on every future read. | `POST /vocab/forms` once to generate+store, then `POST /vocab/extra` (read-only) 2-3 times for the same card and diff the `forms` payload across reads — should be byte-identical. | edge-case-breaker |
| H5 | writing grader | Real, in-category grammar errors the model correctly recognizes but tags with a `reference` key that **isn't** one of the 8 curated keys (there's no `vocabulary`/lexical-choice key at all, despite `vocabulary` being a *scored* criterion) are now silently dropped from `corrections` by `_is_genuine` — a learner who made a real word-choice error gets no correction and no signal it was wrong, even though the text's `vocabulary` *score* may still reflect it. | Submit short writing tasks (any level) containing 2-3 clear word-choice/false-cognate errors ("j'ai regardé la télé" written as "j'ai regardé le télé" is grammar not lexical — pick a genuinely *lexical* slip, e.g. wrong register word, a false-friend translation like "librairie" for "bookstore" misused for "library") alongside 1-2 clear grammar errors; compare `corrections` coverage against a manual read of what's actually wrong in the text — flag any real error that scored lower on `vocabulary`/`coherence` but got zero matching correction. | edge-case-breaker |
| H6 | writing grader | A correction whose `correction` text is grammatically wrong itself, or whose cited `reference` doesn't actually describe the fix (critic/PM's own residual note: "a rewrite the model tags with a wrong rule still gets through"), still passes the filter as long as any curated key is cited and the text changed — i.e. the filter catches *uncited* hallucinations but not *mis-cited* ones. | Submit 3-5 writing tasks per level with a mix of correct and subtly-wrong French; read every surviving correction and judge whether the cited `reference` key plausibly matches the actual excerpt/correction pair. | edge-case-breaker |
| H7 | IPA / stale data | A personal vocab card added **before** this fix (simulating the pre-PR behavior: LLM-guessed English-shaped IPA already stored, e.g. `"hɒrəbəl"`) is **never corrected** by a later voicing, because `personal_api._serve_audio`'s `row.ipa = row.ipa or ipa[:64]` only fills a falsy field — so `GET /vocab/personal/audio/<key>` after the card already has *any* truthy `ipa` leaves the stale/wrong value in place forever, contradicting the "filled on first voicing" framing. This needs a TTS backend to observe the write path; locally `TTS_BACKEND=disabled`, so this is a **code-reading + direct call** check (call `_serve_audio`/`voice_with_ipa` via a short in-repo script using a fake TTS, not the live no-TTS server) rather than an HTTP probe. | Read `app/content/personal_api.py::_serve_audio` + write a short local script (or extend `tests/test_personal_vocab.py`-style harness) that seeds a `UserVocab` row with `ipa="hɒrəbəl"` (simulating a pre-fix row) and a fake TTS that would return the *correct* French IPA, then calls the audio-serving path and asserts whether `row.ipa` changed. | edge-case-breaker |
| H8 | IPA / no-TTS path | With `TTS_BACKEND=disabled` (this round's actual local config), newly-added personal cards and dictionary lookups correctly have `ipa == ""` (never the old English-guessed LLM value) immediately after add/lookup, matching the PR's stated behavior — a straightforward regression check of the already-`fixed` 832, cheap to run live and worth confirming once more since it's now serving real traffic shape (multiple words/levels) rather than the original issue's 3-word repro. | `POST /vocab/personal/from-word` for 8-10 varied words across a1-b2 vocab (nouns, verbs, adjectives, a couple of English/French cognates like "horrible", "amusant" from the original repro); confirm every card's `ipa` field is `""`, and `GET /vocab/personal` afterwards shows the same. | edge-case-breaker |
| H9 | content/forms | Multi-word headwords / fixed expressions added as personal cards with pos=verb or pos=adjective (e.g. "avoir faim", "être content de") feed into `_verb_form`/`_adjective_forms`'s single-word assumptions (`_bare`'s determiner-stripping, `_SUBJECT.match` anchored at string start) and may mangle the phrase rather than leaving it alone. | `POST /vocab/personal/from-word` for 2-3 multi-word phrases with inflecting pos, then `/vocab/forms`; read the result for mangled output (wrong word dropped, elision applied mid-phrase incorrectly). | edge-case-breaker |

## Coverage gaps
- `app/assessment/models.py`'s `explanation: str = ""` default (831's change) —
  no round has checked whether the SPA's writing-feedback UI renders an empty
  `explanation` string sensibly (blank vs. "no explanation" vs. layout gap) — a UI
  question, not charterred this round (API-only scope; flag for a future round
  that includes `qa-browser-tester` on the writing-feedback screen).
- `/vocab/forms` for **nouns** specifically (gender-driven determiner handling,
  `_noun_form`'s `un/une/des` → `le/la/les` rewrite) got lighter hypothesis
  coverage above than verbs/adjectives — if time remains after H1-H9, a tester may
  sample a few noun cards (plural-only nouns like "lunettes", mf nouns like
  "collègue") as a bonus, not required.
- `tidy_forms`'s h-aspiré noun list is implicitly "left to the model" (per its own
  comment) with no rule backstop at all — untested this round; low priority since
  it's explicitly out-of-scope by the code's own design note, not a silent gap.

## Charters (per tester, with id blocks)

- `qa-tester` (persona **edge-case-breaker**, ids **850–865**): chase H1-H4 and H9
  (forms.py rule-engine edge cases: reflexive/impersonal verbs, invariable/
  irregular adjectives, read-path idempotence, multi-word headwords). App base
  `http://127.0.0.1:9200`; sign up with an `@qa.test` email, invite code
  `friend-001`. Use `POST /vocab/personal/from-word` to seed each card, then
  `POST /vocab/forms {"card_key": "<key>"}` (note the `card_key` format is
  `uv:<slug>` per the existing issue reports) to generate/read forms. Since forms
  run at temperature 0, one call per word is enough to be deterministic for H1-H3,
  but sample 2-3x if a result looks borderline (model sampling at temp 0 on Ollama
  isn't always perfectly reproducible across calls). For H4, use `POST /vocab/extra`
  (free, read-only) repeatedly on the same card after generating once, and diff.
- `qa-tester` (persona **edge-case-breaker**, second instance, ids **866–879**):
  chase H5-H8 (writing-grader recall loss / mis-cited corrections, IPA stale-data
  code path, IPA no-TTS regression). For H5/H6: `python -m app.assessment.sync
  <level> content` is already synced; submit via `POST /assessment/tasks/<task_id>/
  submit` for a handful of tasks across a1-b2 with deliberately-authored French
  containing both grammar and lexical/word-choice errors (write the test French by
  hand — don't rely on the model to generate "known-bad" text). For H7, this is a
  **code-level check**, not an HTTP probe — no TTS is wired on this server, so
  write a short standalone script under `/tmp/qa059/` using the app's real DB
  session/models (or extend the pattern in `tests/test_personal_vocab.py`'s
  `FakePiper`) to seed a stale-IPA row and call `_serve_audio`/`voice_with_ipa`
  directly; file the finding as a code-reading-backed issue either way. For H8,
  plain HTTP against the running server (`TTS_BACKEND=disabled` already set).
  Keep both testers' id ranges disjoint; check `qa/issues/` before filing to avoid
  duplicate coverage of the same card/word between the two charters.
- No `qa-browser-tester` this round: all three fixes (830/831/832) are pure
  data/API-contract questions (is this JSON field grammatically correct, is this
  correction array over/under-inclusive, is this IPA string stale) with no new UI
  surface — nothing here needs a browser to observe. The coverage-gap note above
  (empty `explanation` rendering) is the one UI-shaped question, deliberately left
  for a future round rather than charterred here.

## Don't re-file (already settled)
- Issues 830, 831, 832 themselves — closed `fixed` this PR. Only file *new*
  numbers for edge cases the fix didn't cover (see H1-H9 above), and reference the
  closed issue in the new report's Notes for context, don't duplicate the original
  repro.
- The writing grader's "residual" mis-cited-rewrite example noted in 831's own Fix
  section ("remercier de → pour" once in 4 bench grades, filed as a known
  limitation, not re-opened) — H6 above is explicitly chasing *new* instances of
  this same class, which is fine to file fresh if found in different text, but
  don't re-file the exact original example.
- `/speech/*` endpoints 503 with no STT/TTS backend — expected (round 058's own
  note), not a defect.
- Round 058's closed-out hypotheses (raw-ChatML rendering, history trim, opener
  warm-up, authored openers) — unrelated PR, don't re-probe.

## Outcome (round 059)

- **H1** (reflexive verbs losing their subject pronoun because the "je" rescue is
  gated off) — **refuted as literally hypothesized** (9/9 samples, the model always
  included a subject pronoun) but led to a **confirmed, more severe defect in the
  same code path** → issue **853**: reflexive passé composé is wrong 9/9 (drops the
  clitic, uses avoir instead of être, e.g. "j'ai levé" for "je me suis levé"), 2/9
  additionally garbled. Validated, fixed.
- **H2** (impersonal verbs wrongly get "je" prepended) — **confirmed** → issue
  **850** (pleuvoir/neiger). Validated, fixed.
- **H3** (invariable adjectives get a fabricated plural/feminine; beau/nouveau/vieux
  never get a before-vowel masculine form) — **confirmed** on the invariable-adjective
  half → issue **851**. The before-vowel-form half is a real schema gap but ruled
  out of fix scope (the 4-label schema never had that slot, before or after this
  PR — a product decision, not a regression); validated+fixed only for the
  invariable-plural part, per the critic's explicit caveat.
- **H4** (read-path idempotence / legitimate-loanword-char dropped on read) —
  **refuted**: 3x repeat reads were byte-identical; a synthetic non-Latin-char
  injection did get dropped on every read as designed, but no genuine French
  orthography example of a legitimate char ≥ U+0250 could be constructed, so this
  is sound behavior, not a defect. No issue filed.
- **H5** (writing grader structurally drops genuine lexical/word-choice errors —
  no vocabulary key in the curated reference list) — **confirmed** → issue **866**.
  Validated, fixed (added `choix-lexical` to `GRAMMAR_REFERENCES` and the prompt's
  curated list).
- **H6** (mis-cited-but-curated references pass the filter) — **confirmed** → issue
  **867**. Validated as a real, reproducible defect, but **deferred**: it's fresh
  evidence of the exact residual 831's own Fix section already disclosed and
  already tried-and-rejected three mitigations for before shipping; needs a
  stronger grader model, not a filter patch.
- **H7** (personal-card stale pre-fix IPA never corrected by a later voicing,
  because of an `or`-guard asymmetry with the sibling lookup-cache path) —
  **confirmed** via a standalone script (no HTTP — no TTS wired locally) → issue
  **868**. Validated, fixed (now overwrites unconditionally, matching
  `lookup.fresh_lookup`).
- **H8** (fresh personal cards have `ipa == ""` under the no-TTS config, confirming
  832 holds) — **refuted** (i.e. 832's fix holds, no regression): 11/11 fresh cards
  had `ipa == ""`, no stale LLM-guessed value reappeared. No issue filed.
- **H9** (multi-word "avoir X" idioms mangled by the rule engine's single-word
  assumptions) — **confirmed** → issue **852**. Initially triaged `deferred` by
  qa-pm ("needs a prompt rework"), **overturned by qa-critic** to `validated` —
  a cheap rule-level mitigation existed (`_verb_form` already receives the full
  multi-word lemma; restore the dropped complement the same way the existing code
  already restores a dropped "je"). Fixed.

### Issues filed: 850, 851, 852, 853, 866, 867, 868 (7 total)
- **validated → fixed (`done`)**: 850, 851, 852, 853, 866, 868 (6)
- **deferred**: 867 (real defect, same disclosed residual as 831's own Fix
  section; needs a stronger grader model — carry forward to a future round
  scoped to `writing_grader.md` semantic-citation verification)

### Fixes made (dev-fixer, this branch, 686cebd + these commits)
- `app/content/forms.py`: `_IMPERSONAL_VERBS` exclusion from the "je" rescue (850);
  `_INVARIABLE_ADJECTIVES` short-circuit in `_adjective_forms` (851);
  `_restore_complement` for "avoir X" idioms, overlap-guarded (852); `label`
  threaded into `_verb_form`/`tidy_forms` + `_reflexive_passe_compose` scoped to
  exactly that one tense (853).
- `app/assessment/grader.py` + `app/assessment/prompts/writing_grader.md`: added
  `choix-lexical` to the curated reference list, kept in sync (866).
- `app/content/personal_api.py::_serve_audio`: unconditional IPA overwrite,
  matching `lookup.fresh_lookup` (868).
- Tests added/extended in `tests/test_forms.py`, `tests/test_assessment.py`,
  `tests/test_personal_vocab.py` — one regression test per fix, all deterministic
  (FakeRouter/fixed replies, no dependency on the live model).
- Verification: `/tmp/tef312/bin/python -m pytest -q` → **381 passed, 1 skipped,
  0 failed**. `ruff check app tests` → all checks passed. `ruff format --check
  app tests` → clean.

### Verdict: **SHIP** (with one carried-forward item).
Every hypothesis aimed at this PR's actual new code (the `tidy_forms` rule engine,
the `_is_genuine` grader filter, the IPA-fill wiring) found real, in-scope edge
cases the original fix didn't cover — unlike round 058, where every finding
turned out to predate the PR under test, this round's findings are squarely
caused by 686cebd's own new code, which is the expected shape of a round that
immediately follows a fix (a first pass rarely gets every edge case). All 6
cheaply-fixable defects are now fixed, tested, and green; the 7th (867, mis-cited
references) is a known, already-disclosed hard problem appropriately deferred to
a future round rather than blocking this one.
