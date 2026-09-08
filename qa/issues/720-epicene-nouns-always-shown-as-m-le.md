---
id: 720
title: Epicene nouns (témoin, psychologue, notaire...) always tagged "(m)" — never shown as "la" for a female referent
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-09-07
---

## Steps to reproduce
1. Sign up (invite code `friend-001`), get a bearer token.
2. `curl -s -H "Authorization: Bearer <TOK>" http://127.0.0.1:9101/content/vocab`
   and look up the cards for these 8 ids: `psychologue`, `notaire`, `actionnaire`,
   `apatride`, `autochtone`, `camarade`, `specialiste`, `temoin`.
3. All 8 are `"gender": "m", "fem": ""` — e.g.:
   `{"id": "temoin", "fr": "témoin", "en": "witness", "gender": "m", "fem": "", ...}`
   `{"id": "psychologue", "fr": "psychologue", "en": "psychologist", "gender": "m", "fem": "", ...}`
4. In the UI (`web/src/VocabWord.tsx`), any card with `gender === "m"` renders the
   headword with an explicit `(m)` badge next to it (`MARK.m = "(m)"`), and only
   `gender === "mf"` cards ever render a second "la"/feminine form. So a learner
   flipping the "témoin" card in the a2/emergencies deck sees literally "témoin (m)"
   with no indication "la témoin" exists.

## Expected
These 8 nouns are epicene in real French — the article changes with the referent's
sex, not the noun's spelling (`le témoin` / `la témoin`, `le psychologue` / `la
psychologue`, `un(e) camarade de classe`, etc). Marking them plain `gender: m` and
showing an explicit `(m)` badge asserts something that isn't true — a learner would
reasonably conclude "témoin" always takes `le`/is grammatically masculine, and say
"le témoin" for a female witness, which a native speaker would find off. At minimum
the card shouldn't display a misleading `(m)` badge for a noun that's actually
gender-invariant with a variable article.

## Actual
The card shows "témoin (m)" (and likewise for the other 7) with no hint that `la`
is also correct depending on who's being described — same treatment as a truly
masculine-only noun like "chat"/"garçon".

## Notes
This is a genuine judgment call (per the round plan H5), not a clear-cut wrong
answer — the schema's `mf` variant is designed for nouns with a *distinct* feminine
spelling (`ami`/`amie`), and these 8 don't have one, so shoehorning them into `mf`
with an empty `fem` would look worse. But the current `m`-only treatment is also not
neutral: it's an affirmative "(m)" badge, not just an omission, so it actively
teaches a single fixed gender for words that don't have one. A softer fix might be a
distinct badge (e.g. "(m/f)" or "(épicène)") for this handful of nouns rather than
reusing the plain-masculine badge — but that's a design call for pm/critic, not
something to "fix" unilaterally. Filing as `low` given it's a small, correctly-
identified set of words (only 8 total) and the practical harm is a subtly wrong
article choice, not broken functionality.

## Triage
- Explanation: Confirmed via `/content/vocab` and the source YAML (`content/a2/vocab/emergencies.yaml:97` témoin, `content/b2/vocab/psychologie.yaml:50` psychologue, `content/b1/vocab/rights.yaml:85` notaire, `content/b2/vocab/entreprise.yaml:1` actionnaire, `content/b2/vocab/migration.yaml:29` apatride, `content/b2/vocab/histoire.yaml:134` autochtone, `content/a2/vocab/studies.yaml:100` camarade, `content/b1/vocab/health.yaml:44` spécialiste) — all 8 are `gender: m`, `fem: ""`. `web/src/VocabWord.tsx` renders an explicit `(m)` badge (`MARK.m = "(m)"`) for any `gender === "m"` card and only shows a second feminine form for `gender === "mf"`. There's no third state for "invariant spelling, variable article," so these 8 render identically to a truly masculine-only noun like "chat."
- Against spec: Unspecified — the technical plan defines the vocab schema's `gender`/`fem` fields for authoring but doesn't address epicene nouns specifically; this is new territory per the round plan's H5, correctly flagged as a judgment call rather than a clear spec violation.
- Verdict: validated
- Rationale: The `(m)` badge is an affirmative (not neutral) claim about the noun's grammatical gender, and for these 8 words it's incomplete — a learner has no in-app signal that "la témoin" is also correct. Real but narrow (8/1453 words) and low practical harm (wrong article choice, not a broken feature), so `low` severity is appropriate as filed. A reasonable fix is a distinct badge/no badge for this set rather than reusing the plain-masculine marker; leaving the exact UI treatment as a design call per the reporter's own notes.

## Critic
- Challenge: The `mf` schema is explicitly designed for a *distinct feminine spelling*; these 8 words don't have one, so `m` is the only technically-fitting bucket without inventing a third gender state the schema/UI never anticipated. TEF_Platform_Technical_Plan.md is silent on epicene handling, so nothing "required" a different treatment. The (m) badge could be read as marking grammatical agreement (adjectives/articles a learner would independently use with the word), not an assertion that "la X" is wrong — many dictionaries list these as "n." or "m." by convention even though usage varies. Impact is also self-limiting: at A1 (the entry persona for this round) none of the 8 words appear at all — they're all B1/B2 content, i.e. an already more advanced learner who's more likely to know le/la varies for profession nouns.
- Holds up? Yes, on balance. The counter-argument shows this is a defensible, non-obvious design gap rather than a clear defect, which is exactly why the PM and original reporter both framed it as a judgment call — but "no confirmed alternative exists in the schema" doesn't mean the current rendering is correct; it's still an affirmative, incomplete claim shown to a real learner in the UI, verified via source and code trace, and the low severity already accounts for the narrow blast radius (8/1453) and B1/B2-only occurrence. A `low`-severity content nuance is worth a lightweight visual tweak (e.g. dropping the badge for this set, or a distinct marker) without justifying a schema change — proportionate to file, not to reject outright.
- Final verdict: validated

## Fix
Fix: UI-level carve-out — the 8 known epicene ids (temoin, psychologue, notaire,
actionnaire, apatride, autochtone, camarade, specialiste) now render a distinct
"(m/f)" badge instead of the plain "(m)" badge, so the app no longer asserts
they're masculine-only (`web/src/VocabWord.tsx`: added `EPICENE_IDS` set and
branch in the single-gender render path). No content/schema change — matches
the triage/critic's read that a schema change (`mf` with empty `fem`) would look
worse than the current authoring. Regression test added in
`web/src/VocabWord.test.tsx` (asserts "témoin" gets "(m/f)", not "(m)").
