---
id: 1000
title: Inflected adjectives (grandes, petites, longues, sportives, petits, belles) come back as pos noun with an invented gender
severity: medium
area: content
persona: edge-case-breaker
status: deferred
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9302; T=bearer from POST /auth/signup (invite qa062-a). P(w) = POST $B/vocab/personal/preview -H "authorization: Bearer $T" -d {"word":"w"} (fresh, uncached words, real 7B).
1. P(grandes), P(petites), P(longues), P(sportives), P(petits), P(belles).
2. Compare with P(blanches), P(heureuses), P(nouveaux), P(joyeux), which are correctly "adjective".

## Expected
pos adjective, gender empty (the 893 case: "grandes" -> "big (f. pl.)", pos populated, no gender).

## Actual
| word | fr | pos | gender (source) | en |
|---|---|---|---|---|
| grandes | grandes | noun | f (table) | large (f pl) |
| petites | petites | noun | f (table) | small |
| longues | longues | noun | f (table) | long (f pl) |
| sportives | sportives | noun | f (table) | active (f pl) |
| petits | petits | noun | m (table) | small |
| belles | belles | noun | f (table) | beautiful (f. pl.) |
| pendant (preposition) | pendant | noun | m (table) | while during |

## Notes
The noun-only gender gate trusts the model's pos; when the model mislabels an adjective as noun, the gender table/suffix then stamps a gender on it. Same shared cache, so every learner sees "grandes (noun, f)". Also "petites"/"petits" lose the inflection note entirely, and "sportives" -> "active" is the wrong sense (sporty/athletic).

## Triage
- Explanation: resolve_gender (app/content/enrich.py) trusts the model's pos. fr_gender.tsv (Lexique) lists inflected adjective forms (grandes, petites, petits, belles, longues, sportives, pendant all present), so once the 7B says pos=noun the table stamps a gender 'authoritatively'. Root is the 7B mislabelling; the table makes it look certain. Code-level reproduction; live 7B not re-run.
- Against spec: 893: adjective forms get pos populated and no gender.
- Verdict: validated
- Rationale: validated (partly model-quality)

## Critic
- Challenge: Root cause is the 7B labelling an adjective as noun; the Lexique table only amplifies it. No deterministic signal in code distinguishes 'grandes' (adj) from a noun without a POS lexicon, and the prompt cannot be benched here. A prompt tweak or a table-pos guard is a regression risk on every shared-cache lookup, and the PM's own validation is 'partly model-quality' with no live re-run.
- Holds up? No. The deterministic part does not exist at small cost; the remaining part is model quality, which the constraint says to defer. Fixer: do nothing for this issue. Revisit if the table gains a POS column or the prompt can be benched.
- Final verdict: deferred
