---
id: 1002
title: Headword fr gets wrong accents for multiword/long words (à coté de, rez-de-chausseé)
severity: medium
area: content
persona: edge-case-breaker
status: deferred
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9302; T=bearer from POST /auth/signup (invite qa062-a). P(w) = POST $B/vocab/personal/preview -H "authorization: Bearer $T" -d {"word":"w"} (fresh, uncached words, real 7B).
1. P("a cote de") 2. P("rez-de-chaussee")

## Expected
fr "à côté de" and "rez-de-chaussée".

## Actual
- "a cote de" -> fr "à coté de" (wrong: côté), pos preposition
- "rez-de-chaussee" -> fr "rez-de-chausseé" (acute on the wrong-position e; correct is chaussée), pos noun, gender empty
Stored/spoken and shown to every learner via the shared cache (the 891 headword-mangling class, reduced but not gone). Contrast: bibliotheque -> bibliothèque, peut-etre -> peut-être, bien sur -> bien sûr are right. Note P(cote) alone returns côté via the course.

## Triage
- Explanation: _headword (app/content/lookup.py) accepts the model's spelling if the slug matches and accent count >= typed. Misplaced accents (coté, chausseé) have the same slug and more accents, so they pass. Nothing deterministic can know the right accent without a lexicon. Model-quality only.
- Against spec: 891 requires same word, no accent lost; correctness of accent placement is not specified.
- Verdict: deferred
- Rationale: deferred

## Critic
- Challenge: Agree with PM: misplaced accents share the slug and have more accents, so _headword accepts them; nothing deterministic can correct accent placement without a lexicon.
- Holds up? Yes, deferral stands. Model quality only.
- Final verdict: deferred
