# Plan: personalized vocab decks (Speaking-driven, dictionary-enriched)

Ships as small QA'd slices per the delivery workflow. Branches so far:
`feat/anki-vocab-decks` (3a/3b, merged #67), `feat/anki-vocab-import` (Slice 1, open).

## Goal (from the user)

1. Grow / enrich the vocab stack (originally: AnkiWeb decks; now: **dictionary
   enrichment**, with AnkiWeb import as a secondary bulk path).
2. Give each user a **personalized deck driven by which words felt hard**, with
   visible **degrees of difficulty**, so harder words resurface for review more often.
3. **(2026-08-02)** An **Anki-like "build your own deck"** — personal per-user cards,
   fed mainly by the learner's own Speaking practice and auto-enriched by the
   dictionary. See "Direction update" below.

## What already exists (don't rebuild)

The adaptive-difficulty review loop is already built end-to-end:

- **FSRS engine** (`app/srs/`) — per-user cards keyed by vocab id. Grading a card
  `again/hard/good/easy` (`/srs/review`) recomputes an FSRS **difficulty (1–10)** +
  stability and the next `due` date. Grade "Hard" → interval shrinks → the word
  comes back sooner. That *is* "harder words show up more often, per user."
- **Review screen** (`web/src/screens/Review.tsx`) — the due queue with the four
  grade buttons, wired to XP/streaks.
- **Decks screen** (`Decks.tsx` / `Deck.tsx`) — flashcard study; studying a card
  seeds it into the scheduled SRS queue (`/srs/add`).
- **Decks are derived, not authored**: a "deck" = all vocab in a level sharing a
  `tags:` value (48 auto-decks today), plus an "All words" deck. So **adding tagged
  vocab rows creates a new deck for free**, already wired into study → FSRS → Review.

Current stack: ~780 words (a1 214 / a2 206 / b1 180 / b2 180).

So the net-new work is (A) getting more/better vocab from AnkiWeb into the YAML
bank, and (B) *surfacing* the difficulty FSRS already tracks + a dedicated
hardest-words deck. We are **not** re-implementing spaced repetition.

## Direction update (2026-08-02) — dictionary enrichment + personal decks

After the first real AnkiWeb import proved that parsing glosses out of a deck is
brittle (verbose Wiktionary text, no gender, function-word noise → heavy manual
curation), we reshaped the vocab-growth strategy. Decisions:

- **Enrichment = a "dictionary", not deck-gloss parsing.** Given a bare French word,
  produce `{gender, pos, en gloss, ipa}`. Backend: **local LLM (ollama via the AI
  router) + an offline Lexique.org gender table as source-of-truth** (LLM for
  gloss/pos/ipa; Lexique overrides gender for determinism). Chosen over an online
  dictionary API because the self-host box sleeps / network is flaky, and over a
  pure-LLM approach because gender must be reliable. (Online Wiktionary/Wikidata
  remain a fallback data source; commercial dict APIs forbid storing results.)
- **Both audiences, one engine.** The same enrichment powers (a) **personal per-user
  decks** — the Anki-like "build your own deck" the user wants — and (b) cleaner
  **author-side global imports** (`import_anki.py`). Shared infra, two consumers.
- **Primary user entry point = Speaking (Slice 3c).** Words a learner reaches for in
  conversation are the main way cards enter *their* deck; manual "type a word" is
  secondary. This makes 3c the flagship of the personal-deck feature, not a footnote.

New capability implied — **personal decks** (a later slice, see below): a per-user
`user_vocab` store, wired into the existing SRS queue/Review (today `/srs/add` only
accepts global `ContentVocab` ids), with **on-demand TTS** for user words (reuse the
lazy-audio infra from Speaking) instead of pre-built mp3s.

## Licensing reality (decides the import design)

AnkiWeb shared decks are user-uploaded `.apkg` files (a zipped SQLite
`collection.anki2` + media). **Most carry no explicit license.** Wholesale
ingestion + redistribution in this repo repeats the `books/` copyright problem.

**Design rule:** treat a downloaded `.apkg` as a **local, gitignored build input —
a wordlist reference only.** What we commit is our own schema with our own
enrichment (en gloss, gender, pos, tags), which is original expression, not a copy
of the deck. This keeps the committed artifact license-clean and matches the
"authored content" policy. Prefer clearly-permissive decks (CC / public frequency
lists) as sources; record provenance per import.

## Slice 1 — AnkiWeb → vocab import pipeline  *(net-new; primary value)*

**Status: importer built + first deck imported.** `scripts/import_anki.py` +
`tests/test_import_anki.py` (10 tests). Reads a legacy `.apkg` (zip → SQLite
`notes.flds`), cleans HTML/media, strips articles for gender, keeps single words (or
`--keep-phrases`), dedups against all existing ids+lemmas, emits house-style YAML +
stderr review report. `.apkg` inputs gitignored under `imports/`. First real run:
AnkiWeb "French frequency lists/1-2000 on Wiktionary" (CC-BY-SA) → hand-curated into
`content/b2/vocab/actualite.yaml` (33 news/economy cards; b2 180→213), audio
generated. **Learning:** raw frequency dumps are noisy → this motivated the
dictionary-enrichment direction above; heuristic article-based gender only works when
the deck includes articles (the Wiktionary deck didn't). Steps below are the intended
end-to-end flow; step 4 (enrich) should become the dictionary engine.

A build script that turns a chosen `.apkg` into review-ready authored YAML.

`scripts/import_anki.py <deck.apkg> --level a2 --tag voyage`:

1. **Extract** front/back French↔English pairs from `collection.anki2` (stdlib
   `sqlite3` + `zipfile`; strip HTML/media refs). No new runtime dep for reading.
2. **Normalize** to lemma → candidate `{fr, en}`; drop sentences/cloze; keep single
   words + short set phrases.
3. **Dedupe** against all existing global vocab ids (ids are globally unique across
   levels — a collision fails `tests/test_all_levels.py`). Emit only genuinely new
   lemmas; report the overlap count.
4. **Enrich** missing fields — `gender` (noun le/la), `pos`, `id` slug, `tags` — via
   a dictionary/heuristic pass, LLM-assisted where needed. Flag low-confidence rows
   for human review rather than guessing silently.
5. **Emit** `content/<level>/vocab/<tag>.yaml` in the exact existing schema
   (`id/fr/en/gender/pos/tags`), with a header comment recording deck name + source
   URL + import date (provenance).
6. **Human review** the generated YAML (the gate that keeps quality + license clean).
7. `/tmp/tef312/bin/python -m app.content.sync <level>` to load into the DB, then
   `scripts/gen_audio.py <level>` to build the TTS mp3s the flashcards/Review play.

Output: new themed deck(s) appear automatically in Decks; every word is instantly
usable in FSRS review. `.apkg` inputs go under a gitignored `imports/` dir.

**Ship:** one small, high-quality imported deck (e.g. a ~40-word travel/health set)
end-to-end first, QA it, then repeat. Not a mass dump.

## Slice 2 — surface difficulty + a "Hardest words" smart deck  *(enhancement)*

Make the difficulty FSRS already computes visible, and give the user the
"deck of words I find hard" they asked for.

- **Backend:** extend `/srs/queue` (and add `/srs/cards` or `/srs/hardest`) to
  return each card's FSRS **difficulty** (read from the stored state) so the client
  can rank/label. Map the 1–10 value to a small badge scale (e.g. Easy / Medium /
  Hard / Leech).
- **Frontend:** (a) a difficulty badge on Review + Deck cards; (b) a **"Hardest for
  you"** smart deck at the top of Decks = the user's own cards sorted by FSRS
  difficulty (top N), so their personal hard-word deck is one tap away. This is
  per-user and needs no new schema — it reads existing `srs_cards.state`.

Optional follow-ups (separate slices): leech flagging (many `again`s) and a
"struggling words" nudge on the home/path screen.

## Slice 3 — close the Speaking → vocab loop  *(net-new; strongest personalization signal)*

Today Speaking and vocab/SRS are **disconnected**. The only paths that seed a
review card are lesson completion (`app/progress/api.py:143`, `new_vocab`) and the
manual "add to review" button (`/srs/add`). The speech turn stores `transcript`
(what the learner said) + `reply_text` (examiner) in `speech_turns` and stops —
nothing extracts the words the learner **fumbled, avoided, or was handed by the
examiner** and pushes them into their personal deck. That transcript is the richest,
most personal difficulty signal we have, and it's currently thrown away.

Close the loop: after a turn, surface the useful vocabulary from the exchange and
let the learner seed it into their SRS deck (reuse `seed_cards` — the machinery
already exists; no new SRS work).

### When to ask for review: **end of conversation, not per turn** (decided)

Per-turn review (a chip list after every spoken turn) is rejected: it breaks the
fluency/immersion that is the whole point of speaking practice, is noisy/repetitive
(same word across turns → decision fatigue), and puts an extra LLM call on the hot
path per turn. Review happens **once, when the learner ends the conversation** — a
consolidated, deduped, ranked list, like an examiner debrief at the end of a TEF
oral. This is non-interruptive and needs one extraction pass, not N.

### The boundary problem (why this needs a small addition)

There is **no session concept today**: `speech_turns` rows are individual,
`_recent_history` just pulls the last 3 turns per user, and the frontend holds turns
in local `useState` with no "end" action. But we **already persist every turn's
`transcript` + `reply_text`** — so we don't need a per-turn candidate buffer/table;
we only need a way to group a conversation's turns and a moment to process them.

### Architecture — decouple extraction (compute) from presentation (UX)

1. **Add `session_id` to `SpeechTurn`.** The client generates a UUID when a
   conversation/topic starts and sends it with each `/speech/turn`. Minimal
   migration; also improves history grouping. (A conversation = one topic session,
   or a free-talk session until reset.)
2. **"Finish & review" action** in the Speaking UI ends the conversation and calls
   a new endpoint, e.g. `POST /speech/session/{session_id}/vocab-review`, which:
   - reads *that session's* stored turns (transcripts + replies) — data already
     persisted, so no hot-path work and nothing extra to store;
   - runs **one lightweight extraction LLM pass** → target French lemmas worth
     reviewing (missed / misused / examiner-supplied), each with a short gloss;
   - **resolves** each lemma against `ContentVocab` ids and returns a deduped,
     ranked candidate list.
3. **Resolve tiers:**
   - **Cheap/clean tier (ship first):** keep only lemmas that map to an existing
     vocab id → `seed_cards(user, ids)`. Known words → clean cards, no authoring,
     license-free.
   - **Rich tier (Slice 3c — the flagship personal-deck path):** lemmas with no
     match run through the **dictionary enrichment engine** (LLM + Lexique gender)
     and are offered for the learner's **personal deck** (`user_vocab`), not the
     global bank. Speaking discovers the gap; the dictionary fills it; the word
     becomes a private card in the user's FSRS review. Slots into step 2's resolve
     without changing the timing model.
4. **Presentation:** the endpoint's list renders as a "Add these to your review
   deck" confirm-chip debrief (learner confirms — never silent auto-seed, so the
   deck stays trustworthy). Seeded words ride the existing FSRS loop (Slice 2 makes
   their difficulty visible).

### Abandonment is handled for free

Because transcripts persist per session, a learner who never taps "Finish" loses
nothing: the same endpoint can be re-run for a past `session_id`, so we can resurface
it next visit — *"3 words to review from your last conversation."* No candidate
buffer, no lost signal. (Client should also offer the review if they navigate away
with ≥1 turn in the session.)

**Ship order within the slice:** (a) `session_id` + cheap-tier endpoint +
confirmed-seed UI at end-of-conversation → QA; (b) last-session resurface nudge;
(c) rich tier once Slice 1's enrichment path exists. Per-turn *live* hints (a
different feature — real-time coaching, not review-seeding) stay out of scope.

## Slice D — dictionary enrichment engine  *(shared infrastructure)* ✅ built

The foundation both personal decks and cleaner imports need. Built on
`feat/vocab-enrich` (`app/content/enrich.py` + `tests/test_enrich.py`, 14 tests).

- **Service:** `enrich(router, word) → (Enrichment{fr, en, pos, gender, ipa,
  gender_source}, llm_result)`. Two decoupled layers: `propose` runs one cheap LLM
  pass (new `vocab_enrich` JSON profile, cached 7d) for gloss/pos/ipa; then
  `resolve_gender` applies a **deterministic backstop** because a local model gets
  French gender wrong too often to trust: **table > high-confidence suffix rule
  (‑tion/‑té→f, ‑ment/‑eau→m) > model guess > "" (unresolved)**. `gender_source`
  records which layer won, for confidence/flagging.
- **Gender table (source of truth):** `GenderTable.load()` reads a TSV at
  `app/content/data/fr_gender.tsv` — seeded with common words + suffix-rule
  counter-examples (silence, musée = m). **Drop a full Lexique383 extract at that
  path to widen coverage with zero code change** (the "bundle Lexique" step, deferred:
  it's a ~5 MB download and the seed + suffix rules already cover the common cases).
- **Consumers:** `import_anki.py` enrichment step, Speaking rich tier (3c), and the
  personal "add card" flow (E). Offline on the box (ollama + local table); no external API.

## Slice E — personal user decks (Anki-like)  *(the "build your own deck" ask)* ✅ built

Built on `feat/personal-decks`. `user_vocab` table (migration 0018) + `/vocab/personal`
API (preview→enrich, add, my-deck list, lazy-TTS audio) + `MyDeck` screen. Personal
card keys are namespaced `uv:<slug>`; `/srs/queue` routes those to `user_vocab` and
everything else to `ContentVocab`, so personal cards ride the exact FSRS loop with no
new scheduling. Audio synthesized on demand (cached on the row), no pre-built mp3.
Backend 8 tests + FE MyDeck test; suite 278 pass, FE 39 pass.

### Original design notes

Let each user keep private cards, not just study the shared bank.

- **Storage:** `user_vocab` (user_id, id, fr, en, gender, pos, ipa, source). Distinct
  from global `ContentVocab`.
- **SRS wiring:** the SRS `card_key` is already an unconstrained string with no FK —
  extend `/srs/add`, the queue, and Review to resolve a card from *either*
  `ContentVocab` or `user_vocab`. Personal cards then ride the exact FSRS loop +
  difficulty surfacing (Slice 2) with no new scheduling.
- **Audio:** synthesize user-word audio **on demand** (reuse the Speaking lazy-TTS +
  object-storage cache) instead of pre-built mp3s.
- **Entry points (priority order):** Speaking (3c) → optional manual "type a word →
  dictionary preview → add" → (later) paste-a-list / upload-own-`.apkg`.
- **UI:** a "My deck" view alongside the shared Decks screen.

## Out of scope (explicitly)

- Re-implementing SRS/scheduling (FSRS already does it).
- Committing raw `.apkg` files or their media.
- Exporting the app's vocab *as* an Anki deck (a valid separate idea — the reverse
  direction via `genanki` — but not this plan).

## Sequence & status

Done:
1. **Slice 3a** — Speaking→vocab loop, cheap tier. ✅ merged (#67) + deployed.
2. **Slice 3b** — last-session resurface nudge. ✅ merged (#67) + deployed.
3. **Slice 1** — importer + first imported deck (`actualite` b2). ✅ merged (#68)
   + deployed.
4. **Slice D** — dictionary enrichment engine (`enrich()` + gender table + suffix
   backstop + `vocab_enrich` profile). ✅ built on `feat/vocab-enrich`; **QA → PR
   pending**. Prereq for 3c and E.

Next (revised after the 2026-08-02 direction update):
5. **Slice E** — personal user decks. ✅ merged (#70) + deployed.
6. **Slice 3c** — Speaking rich tier: unmatched spoken words → dictionary enrich →
   personal deck. ✅ built on `feat/speaking-rich-tier`. `resolve_new_words()` returns
   extracted lemmas not in the content bank and not already personal cards; the
   `/speech/session/{id}/vocab-review` response carries them as `new_words`; a new
   `POST /vocab/personal/from-word` enriches (D) + adds (E) in one budget-gated call;
   Speaking's SessionReview shows a "New words for your deck" one-click-add section.
   → QA → PR.
7. **Slice 2** — difficulty surfacing + "hardest for you" deck (applies to both
   global and personal cards). → QA → PR.
8. Deploy to the box after each merge.

Dependencies: 3c needs D + E; E needs D. Slices 1 and 2 are independent. The
`import_anki.py` global-import path continues to exist but is now the *secondary*
way vocab enters the app — personal decks (E, driven by 3c) are primary.
