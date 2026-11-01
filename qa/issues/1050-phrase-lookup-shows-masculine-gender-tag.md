---
id: 1050
title: Multi-word phrase added to My deck is tagged "(m)" masculine
severity: low
area: web
persona: absolute-beginner
status: done
found: 2026-10-31
---

## Steps to reproduce
1. Sign in, go to /my-deck (level A1).
2. Type `je voudrais réserver une table pour quatre personnes ce soir`, press Enter / Look up.
3. Observe the preview, then press "Add to my deck" and observe the saved card.

## Expected
A full sentence/phrase has no grammatical gender, so no gender tag is shown (as for other non-noun entries).

## Actual
Preview and saved card both show the headline followed by "(m)" (gloss "I would like to reserve a table for four people this evening"). A beginner would read this as "this sentence is masculine". Single noun "cacahuète" correctly shows "(fe)".

## Notes
LLM gender gate in enrich.py applies to a multi-word phrase (pos probably noun or empty). Suggest suppressing gender when the headword contains spaces / is not a noun. Related to 1000/1004 theme (pos/gender mismatch).

## Triage
- Explanation: resolve_gender in enrich.py returns early only when pos is non-empty and not noun ('if pos and pos != noun'). A sentence with empty/unmapped pos falls through to suffix_gender, and 'soir' hits the -oir masculine rule (also a phrase ending in -tion/-ment would get a gender). Code-level; not reproduced in browser.
- Against spec: Gender applies to nouns only (893 / enrich docstring); phrases have none per VocabWord comment ('verbs, adverbs, phrases…' show no mark).
- Verdict: validated
- Rationale: validated

## Critic
- Challenge: Only the LLM-gender and suffix paths are touched; however resolve_gender's suffix step runs for empty pos and for multiword text (confirmed enrich.py:136-144: only non-empty non-noun pos returns early), so 'soir' -> -oir -> m on a sentence is deterministic, not model noise. Real learner-visible nonsense, but tag-only.
- Holds up? Yes, narrowed. Fixer scope: in resolve_gender, skip the suffix rule and the LLM guess when the word contains whitespace (keep the table lookup first so real multiword nouns like 'pomme de terre' still resolve if listed). Do not touch the prompt. Add a test: resolve_gender('je voudrais ... ce soir','', 'm') == ('','').
- Final verdict: validated

## Fix
resolve_gender (app/content/enrich.py) returns no gender for multi-word text after the table lookup, so phrases skip the suffix rule and LLM guess. Test: tests/test_enrich.py::test_phrase_has_no_gender.
