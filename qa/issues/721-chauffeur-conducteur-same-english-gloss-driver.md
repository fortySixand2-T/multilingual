---
id: 721
title: "chauffeur" (a1/jobs) and "conducteur" (b1/mobility) share the identical English gloss "driver"
severity: low
area: content
persona: edge-case-breaker
status: rejected
found: 2026-09-07
---

## Steps to reproduce
1. Sign up (invite code `friend-001`), get a bearer token.
2. `curl -s -H "Authorization: Bearer <TOK>" "http://127.0.0.1:9101/content/vocab" |
   python3 -c "import json,sys; d=json.load(sys.stdin)['cards']; print([c for c in d
   if c['id'] in ('chauffeur','conducteur')])"`
3. Result:
   `{"id": "chauffeur", "fr": "chauffeur", "en": "driver", "level": "a1", "tags": ["jobs"], ...}`
   `{"id": "conducteur", "fr": "conducteur", "en": "driver", "level": "b1", "tags": ["mobility"], ...}`
   Both cards have the exact English gloss `"driver"` — no qualifier distinguishing
   them.

## Expected
Two different French headwords teaching the same English word should carry glosses
that disambiguate them for the learner (e.g. `"driver (job)"` for `chauffeur` vs
`"driver (of a car)"` for `conducteur`, or similar), especially since they land in
SRS review as separate cards a learner is expected to recall by translating "driver"
→ French. As written, a learner reviewing either card back-to-front (En → Fr) has no
way to know which French word is being asked for — both prompts read "driver".

## Actual
Both cards use the bare gloss "driver" with no disambiguating text, despite genuine
semantic differences (chauffeur = person whose job is driving, e.g. a taxi/bus
driver; conducteur = the person currently driving/operating a vehicle, more general).

## Notes
Found via a bank-wide scan of the 32 new decks for cards sharing an identical
English gloss but a different French headword — this was the only exact match
found (out of ~640 new entries), so it's an isolated case, not a systemic pattern.
Low severity: doesn't teach anything factually wrong, just creates SRS review
ambiguity/confusion between two legitimately different words.

## Triage
- Explanation: Confirmed in source — `content/a1/vocab/jobs.yaml:57-60` (`chauffeur`, `en: driver`, `gender: mf`) and `content/b1/vocab/mobility.yaml:119-122` (`conducteur`, `en: driver`, `gender: mf`) both carry the bare English gloss `driver` with no qualifier. The vocab schema has no separate "disambiguation" or "usage note" field — `en` is the only gloss shown on the card front/back and the only prompt used for En→Fr recall.
- Against spec: Unspecified — the technical plan doesn't mandate gloss disambiguation for near-synonym pairs; this is a content-authoring quality gap, not a schema/rule violation.
- Verdict: validated
- Rationale: Genuine SRS review ambiguity — a learner prompted with "driver" (En→Fr direction) has no way to know which of two legitimately different French words (chauffeur = professional driver-by-trade; conducteur = the person currently operating the vehicle) is being asked for. Isolated case (1 pair out of ~640 new entries per the reporter's bank-wide scan), doesn't teach anything factually wrong, so `low` severity is appropriate as filed. Straightforward fix: add a parenthetical qualifier to one or both glosses (e.g. "driver (professional)" / "driver (of a vehicle)").

## Critic
- Challenge: The "isolated case" framing is the key claim to attack, and it doesn't survive: `grep -h "^  en:" content/*/vocab/*.yaml | sort | uniq -d` finds 5 duplicate-gloss pairs bank-wide, not 1 — `driver` (chauffeur/conducteur, this round's new pair), plus 4 pre-existing pairs never touched by this commit: `platform` (quai/plateforme), `profit` (bénéfice/profit), `tax` (taxe/impôt), `teacher` (professeur/enseignant). All 4 pre-existing pairs live in files outside the 32 new decks (`transport.yaml`, `technology.yaml`, `actualite.yaml`, `economie.yaml`, `money.yaml`, `argent.yaml`, `school.yaml`, `education.yaml`) and none has ever been filed as a bug across 50+ prior QA rounds. This is a recurring, accepted pattern in a leveled curriculum — a concrete concept resurfacing with a more advanced synonym at a higher CEFR level (professeur→enseignant, taxe→impôt) is normal authoring, not an authoring slip. Separately, review in this app is flip-and-self-grade (`web/src/screens/Review.tsx`: "Show answer" then the learner marks their own recall) — not an auto-graded fill-in-the-blank — so a shared gloss never produces a wrong/graded answer; the learner sees the correct French word the moment they flip, same as any other card.
- Holds up? No. The PM's rationale rests on this being an isolated authoring gap worth a content tweak, but the bank already contains 4 structurally identical pairs that predate this round and were never flagged, which shows the team treats same-English-gloss-different-level pairs as acceptable by precedent, and the "SRS review ambiguity" harm doesn't actually materialize given the self-graded flip-card mechanic (no wrong answer is ever recorded). Filing chauffeur/conducteur while leaving the 4 precedent pairs unfixed would be inconsistent scope creep on a content pattern the bank already relies on.
- Final verdict: rejected
