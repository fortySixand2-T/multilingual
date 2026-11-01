---
id: 1004
title: Fresh nouns can come back with pos noun but no gender (éléphant, rez-de-chaussée)
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: B=http://127.0.0.1:9302; T=bearer from POST /auth/signup (invite qa062-a). P(w) = POST $B/vocab/personal/preview -H "authorization: Bearer $T" -d {"word":"w"} (fresh, uncached words, real 7B).
P(elephant), P(rez-de-chaussee).

## Expected
gender m for both (gender is a core field for a noun).

## Actual
elephant -> fr éléphant, pos noun, gender "", gender_source "". rez-de-chaussee -> pos noun, gender "". The model's gender is silently dropped when it returns anything outside m/f/mf and there is no table entry, leaving the card without an article cue.

## Notes
Most other fresh nouns (courage, trottoir, fleuve, vendeuse) resolve fine, so this is an intermittent gap, not systematic.

## Triage
- Explanation: _parse_enrichment keeps gender only if exactly in ('m','f','mf'); 'masculine', 'm.', 'M', 'masc' become ''. resolve_gender then has no table entry (éléphant not in tsv) and no suffix rule, so noun with ''. rez-de-chaussée has no reliable signal (model-only).
- Against spec: 893/enrich docstring: model guess is the fallback after table and suffix.
- Verdict: validated
- Rationale: validated

## Critic
- Challenge: The PM's mechanism (model replies 'masculine'/'M'/'masc') is a guess; the report never captured the raw model reply, and for rez-de-chaussee the PM admits there is no signal. elephant is not in the table and has no suffix rule, so the likelier cause is the model simply returning '' or a wrong pos, which no parse tweak fixes. Intermittent, low severity, and the gender is shown only as a cue. A parse tweak is speculative: it may not fix the reported case.
- Holds up? No: the cause is unproven and the fix may be a no-op. Conservative default is no change. Optional if the fixer wants it: none required. Closing without a change; re-file with the raw model reply if gender is shown to be dropped by the strict ('m','f','mf') check.
- Final verdict: deferred

## Fix
enrich() now takes the headword chooser and resolves pos and gender on the kept spelling, not the typed one, so elephant -> éléphant m (table). GenderTable.get also tries the oe spelling of œ. Model gender words (masculine, f.) are normalised. Tests: test_gender_resolves_on_the_kept_headword, test_accentless_input_gets_lexique_accents.
