---
id: 891
title: Accentless input is stored and voiced as typed instead of the dictionary headword (eleve, francais, reponse, apres, oeuf, cacahuetes)
severity: high
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: B=http://127.0.0.1:9300; T=<bearer from POST /auth/signup, invite qa060-b>. P(w) = curl -s $B/vocab/personal/preview -H "authorization: Bearer $T" -H 'content-type: application/json' -d '{"word":"w"}'
1. P(eleve), P(francais), P(reponse), P(apres), P(cacahuetes), P(oeuf), P(education).
2. Compare with P(cacahuete) and P(foret), which are corrected.

## Expected
fr is the accented headword: élève, français, réponse, après, cacahuètes (or cacahuète), œuf/oeuf, éducation. This fr is what Piper reads and what the learner studies.

## Actual
fr returned verbatim: eleve, francais, reponse, apres, cacahuetes, oeuf, education. Normalisation is inconsistent: cacahuete->cacahuète, foret->forêt, peut etre->peut-être, naive->naïve, garcon->garçon are fixed, eleve etc. are not (LLM-dependent, and then cached for everyone). Course words (ecole, etudiant, hopital) are corrected only because they hit the course table, but those return ipa "" and audio_url null (see 874).

## Notes
Also a la maison -> fr "a la maison" (should be "à la maison"), pos "preposition", ipa "a la mɛzˈɔ̃" (nasal where mɛzɔ̃ is right-ish; stress marks, see 882). Suggest validating LLM fr against accent-folded input and rejecting unaccented output when an accented headword exists.

## Triage
- Explanation: Confirmed by code. `enrich.py::enrich` returns `Enrichment(fr=lemma, ...)` where lemma is the article-stripped typed text; `_ENRICH_SYSTEM` asks the LLM only for en/pos/gender, never a headword. `fresh_lookup` stores and voices that typed `fr`. So accentless input is stored/voiced as typed (eleve, cacahuetes). Course words look "corrected" only via `find_content_match` (accent-folded match to content_vocab, returning the course `fr`).
- Against spec: Requirement from PO: accentless input must not be stored or voiced as typed with nonsense IPA. Lexique->IPA pipeline is out of scope; a small curated mechanism is allowed.
- Verdict: validated
- Rationale: Root cause of the user's complaint (word and pronunciation made no sense). Minimum safe design: (1) extend the enrich prompt/JSON with `"fr"`: the correctly accented dictionary headword (singular/lemma form is NOT required; keep inflection as typed, e.g. cacahuètes) and parse it in `_parse_enrichment`. (2) Accept the LLM `fr` only if `slugify(llm_fr) == slugify(typed)` (accent/case/ligature fold equal, tolerate œ via the 871 map) and it is non-empty and <=128; otherwise fall back to typed. This blocks the model swapping in a different word. Never trust it to ADD letters. (3) Optional tiny curated map (accentless->headword for a few dozen high-frequency traps: eleve, francais, reponse, apres, ete, tres, deja, oeuf, ...) checked before/over the LLM, same file style as `fr_gender.tsv`; keep small, Lexique is next slice. (4) Voice and IPA the headword `fr`, never the typed form; the shared IPA-normalize fn (869/875/882/873) applies to that. (5) If typed is accentless and the final fr is still accentless AND differs from nothing known, it is stored as typed (cannot do better) -- acceptable, as the headword check then equals typed. (6) Headword check on cache hit as in 890. (7) Backfill script (idempotent, `--dry-run` default, NOT run on live DB): delete `vocab_lookup` rows (and their clips) whose `fr` is pure ASCII or whose slug collides (il/œil family) so they regenerate lazily with the new logic; for `user_vocab` rows whose fr equals the ASCII fold of a now-known headword, only REPORT (don't rewrite user data) unless `--apply`; re-derive IPA through the shared normalize fn. Tests: mock router returns fr "élève" for "eleve"; rejected when LLM returns an unrelated word; cache hit with accented input over accentless row re-enriches.


## Critic
- Challenge: Scope creep: the PM stacks a curated accentless->headword map, a destructive backfill and prompt changes. A 7B model may not return accents reliably.
- Holds up? Core holds (LLM returns headword, accepted only if slugify/lookup_slug(llm_fr)==lookup_slug(typed), non-empty, <=128; voice and IPA the headword; fallback to typed). Trimmed: (a) SKIP the curated map (optional in the triage) unless tests show the LLM misses the trap list; it is a second source of truth and Lexique territory. (b) Backfill must NOT delete 'rows whose fr is pure ASCII': that would purge every legitimate ASCII word (chat, avion, sur) and force re-LLM of the whole cache. Backfill deletes only deterministic poison (lookup_slug(row.fr) != row.slug, 871) and re-derives IPA; ASCII-fr rows and user_vocab are report-only (dry-run default, never auto-rewriting user data, not run on live by the fixer). (c) Prompt edit limited to adding the fr field; no gloss-quality tweaks (893). Cached rows fixed lazily via 890's cache-hit check.
- Final verdict: validated

## Fix
The enrich prompt/JSON gains `fr` (accented headword). `lookup._headword` accepts it only if `lookup_slug` matches the typed word, it loses no accent and is <=128 chars, else the typed form is kept; the headword is what is voiced and IPA'd. No curated map. Backfill only deletes slug-poisoned rows and reports (never rewrites) unaccented cards whose headword is known. 892 acceptance: preview of cacahuetes voices cacahuètes.
- Files: `app/content/enrich.py`, `app/content/lookup.py`, `scripts/backfill_ipa.py`
- Tests: `tests/test_personal_vocab.py::test_accentless_input_is_stored_and_voiced_as_the_headword, test_headword_from_the_model_is_only_accepted_for_the_same_word`
