# Plan: AnkiWeb-sourced vocab + user-personalized difficulty decks

Branch: `feat/anki-vocab-decks` (off `main`). Ships as small QA'd slices per the
delivery workflow.

## Goal (from the user)

1. Use AnkiWeb shared French decks to **grow / enrich the vocab stack**.
2. Give each user a **personalized deck driven by which words felt hard**, with
   visible **degrees of difficulty**, so harder words resurface for review more often.

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

**Status: importer built** — `scripts/import_anki.py` + `tests/test_import_anki.py`
(10 tests). Reads a legacy `.apkg` (zip → SQLite `notes.flds`), cleans HTML/media,
strips articles for gender, keeps single words (or `--keep-phrases`), dedups against
all 780 existing ids+lemmas, emits house-style YAML with a provenance header and a
stderr review report. `.apkg` inputs are gitignored under `imports/`. **Not yet run
against a real deck** (needs a chosen `.apkg`); enrichment is heuristic (LLM-assist =
follow-up). Steps below are the intended end-to-end flow.

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
   - **Rich tier (later — the "word suggestion" idea, after the transcript loop is
     proven):** lemmas with no match flow through the *same* enrichment/authoring
     path as the AnkiWeb import (Slice 1). Speaking discovers the gap; the import
     pipeline fills it. This slots into step 2's resolve without changing the
     timing model.
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

## Out of scope (explicitly)

- Re-implementing SRS/scheduling (FSRS already does it).
- Committing raw `.apkg` files or their media.
- Exporting the app's vocab *as* an Anki deck (a valid separate idea — the reverse
  direction via `genanki` — but not this plan).

## Sequence

Decided order (Slice 3 leads; word-suggestion/rich tier comes after the transcript
loop is proven):

1. **Slice 3a** — Speaking → vocab loop, *cheap tier*: `session_id` + end-of-
   conversation `vocab-review` endpoint (existing-id resolve only) + confirm-seed UI
   → QA round → PR → merge.
2. **Slice 3b** — last-session resurface nudge **(built)**: `GET /speech/last-session`
   returns the most recent prior session; the Speaking screen offers "Review words
   from your last conversation" (opt-in, no auto-billing). No "reviewed" flag needed
   — `resolve_to_vocab` already excludes words already in the deck, so a re-reviewed
   session returns an empty list. → QA → PR → merge.
3. **Slice 1** — AnkiWeb import pipeline + first imported deck (also builds the
   enrichment path the rich tier needs) → QA → PR → merge.
4. **Slice 3c** — Speaking loop *rich tier*: unmatched lemmas → Slice 1 enrichment
   → QA → PR → merge.
5. **Slice 2** — difficulty surfacing + hardest-words deck → QA → PR → merge.
6. Deploy to the box after each merge.

Slices stay independent; this is the intended path, not a hard dependency chain
(only 3c depends on 1). Slice 3 leads because its difficulty signal comes from the
user's own speech rather than a grade button — closest to the original "deck of
words I found hard" goal.
