---
name: content-expansion
description: Expand the French content bank (vocabulary decks, lessons, path units) for a CEFR level. Use when asked to add vocabulary, add or extend lessons, add a level, or fix lesson↔vocab coherence. Encodes the invariants, the authoring traps, and the per-slice delivery rhythm.
---

# Expanding the content bank

## What this system is actually for

Every rule below serves one goal: **a learner is never quizzed on a word they
were never taught, and never taught a word they can't practise.**

Three data structures have to agree, and nothing in the app forces them to:

| structure | what it drives | breaks if wrong |
|---|---|---|
| `content/<lvl>/vocab/*.yaml` | deck tiles (grouped by `tags`), SRS cards | word invisible, or duplicate DB key |
| `content/<lvl>/lessons/*.yaml` | the Learn path; `new_vocab` **seeds SRS cards** | learner reviews words never shown |
| `content/<lvl>/path.yaml` | unit order and unlocks | lesson unreachable |

`new_vocab` is the join. It is not a label — `app.progress.api.seed_cards` turns
it into review cards the moment a learner first passes the lesson. **A word in
`new_vocab` that the lesson's own exercises never show is the central defect
this skill exists to prevent.**

## Non-negotiable invariants

`python scripts/check_content.py [levels...]` checks all of these, and
`tests/test_content_invariants.py` runs it in CI. **Run it before pytest** — it
gives a readable answer where the loader gives a nested Pydantic error.

1. **Vocab ids are globally unique across levels.** They are DB primary keys
   *and* FSRS card keys. `couverture` (a1 blanket) vs `couverture` (b2 press
   coverage) is a collision — rename one (`couverture_presse`).
2. **Exercise ids are globally unique.** Copy-pasting a lesson and forgetting to
   renumber silently shadows another lesson's exercise.
3. **Every `new_vocab` word is shown by that lesson's own exercises.**
4. **Every vocab word is introduced by some lesson** — otherwise it is reachable
   only by browsing its deck.
5. **Every vocab word has audio** at `content/<lvl>/audio/<id>.mp3`
   (plus `<id>_f.mp3` when `gender: mf`). Audio is a *build artifact* — never
   hand-made. Regenerate with `python scripts/gen_audio.py <level>`.
6. **Every vocab word has `tags`** — a word with no tag appears under no deck.
7. **Every lesson is referenced by a `path.yaml` unit.**
8. `gender: mf` requires a genuinely different `fem` spelling. Epicene nouns
   (*témoin*, *psychologue*) have no schema slot — the UI handles them via
   `EPICENE_IDS` in `web/src/VocabWord.tsx`.

## The YAML traps

These load as **valid YAML** and fail later, so the error never points at the
cause. They have bitten this repo repeatedly.

```yaml
en: true                              # BOOLEAN, not the string "true" (gloss of *vrai*)
- [vrai, true]                        # same, nested inside match_pairs
- [alternance, co-op, work-study]     # unquoted comma -> a 3-ITEM pair
tokens: [on, off, yes, no]            # word_bank tiles that are YAML booleans
```

**Rule: quote every flow-list value containing a comma, and every value that is
a YAML boolean token** (`true/false/yes/no/on/off`).

## Adding vocabulary

A new `content/<lvl>/vocab/<theme>.yaml` becomes a deck tile with **zero code
change** — `web/src/screens/Decks.tsx` groups by `tags`.

```yaml
- id: depanneur          # globally unique, ascii, snake_case
  fr: dépanneur
  en: corner store (Québec)
  gender: m
  pos: noun
  tags: [places]         # drives the deck tile
```

Then: `python scripts/gen_audio.py <level>` → **wire every new word into a
lesson's `new_vocab`** (invariant 4) → give it an exercise (invariant 3).

Do not cap deck size arbitrarily. Depth belongs where the theme justifies it.

## Adding or extending lessons

```yaml
id: animals-01
title: "Animals"
grammar_point: "definite article le/la with animals"
grammar_category: "Articles & determiners"
est_minutes: 8                 # ~1 per exercise; bump it when you add exercises
new_vocab: [chien, chat, ...]  # SEEDS SRS CARDS
pass_threshold: 8.0            # 0-10 scale
exercises: [...]               # ids: <lesson-id>.eN
```

Exercise types: `match_pairs`, `mcq`, `word_bank`, `listen_type`, `translate`.
`listen_type.audio_ref` must point at a real file under `content/`.

**Cover the words, then make the coverage worth doing.** The check only proves a
word is *shown*; it cannot tell a good exercise from filler.

- Generate the `match_pairs` baseline **from the vocab bank**, never by hand —
  then `fr`/`en` physically cannot drift from the deck.
- Balance chunks (6 words → 3+3, not 5+1). A one-pair `match_pairs` is
  trivially solvable and reads as filler.
- A 1–2 word remainder should ride on the lesson's **existing** `match_pairs`
  rather than become a near-empty exercise.
- Add at least one exercise that **uses** each batch of new words inside the
  lesson's own `grammar_point`, so the word is practised, not just matched.
- If a word is only ever shown as a conjugated form the headword match can't
  see, record it in `KNOWN_CONJUGATED_ONLY` — do not loosen the matcher.

New units also need a `path.yaml` entry, chained
(`{ type: all_of, requires: [<previous unit id>] }`), and an icon in
`UNIT_ICONS` in `web/src/screens/Path.tsx` or the unit renders a fallback 📘.

## Delivery rhythm

Ship **one level per PR**, smallest slice first to prove the approach before
committing to the large ones. Per PR:

1. branch (never commit to `main`)
2. author
3. `python scripts/check_content.py` → `ruff check .` → `ruff format --check .`
   → `pytest -q`
4. **read a sample of the generated output** — the checks pass on filler
5. append to `CHANGELOG.md`
6. PR, wait for all four CI jobs, merge on green

If a fix must land against a known-broken baseline, **land the failing check
first**, carve the existing failures into `KNOWN_GAPS`, and delete entries as
they are fixed. `check_known_gaps_not_stale` makes the carve-out shrink-only, so
it can never outlive the defect.

Known flake: `web/e2e/specs/vocab-deck.spec.ts:30` on chromium — re-run the job
before investigating.

## Deploying

Content changes need a redeploy to reach the box:

```bash
ssh rohith@10.0.0.54
cd ~/projects/multilingual && git pull
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Back the DB up first. The box carries an **uncommitted `docker-compose.yml`**
LAN-Ollama tweak — check `git status` there before pulling.
