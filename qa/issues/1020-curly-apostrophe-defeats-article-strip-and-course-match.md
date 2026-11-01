---
id: 1020
title: Preview with a curly apostrophe (l’eau, l’avion, L’été) skips article stripping and course matching, giving wrong gender/meaning
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: http://127.0.0.1:9302 (qa062-app), token from POST /auth/signup (invite qa062-b).
1. POST /vocab/personal/preview {"word":"l'eau"} (straight apostrophe)
2. POST /vocab/personal/preview {"word":"L’eau"} (U+2019, what iOS/Android/Word keyboards type)
3. Same with "l’ordinateur", "l’avion", "L’été", "aujourd’hui".

## Expected
Same result as the straight apostrophe: article stripped, course word recognised.

## Actual
Step 1: fr "eau", gender f, in_course a1. Step 2: new LLM lookup, no in_course:
`{"fr":"L’eau","en":"Water","pos":"noun","gender":"m","ipa":"lo","gender_source":"suffix","audio_url":".../l_eau"}`
(wrong gender, capitalised meaning, headword keeps the article, IPA "lo"). "L’été" -> gender f (wrong, summer is m), fr "L’été", slug l_ete, vs "l'été" -> "été" m. "l’avion" -> fr "l’avion", en "the airplane", gender "" (course has avion m). "l’ordinateur" same. Adding these makes a duplicate personal card of a course word with the article baked in.

## Notes
strip_leading_article (normalize_lemma) only knows the ASCII apostrophe; normalize U+2019/U+2018 to "'" before stripping/matching. Also affects /vocab/personal and /from-word.

## Triage
- Explanation: strip_leading_article (enrich.py) _ARTICLES lists only ASCII apostrophe forms (l', d'), so l’eau keeps its article; find_content_match _norm/_deaccent also miss it; slug becomes l_eau. Confirmed in code (U+2019 never normalised).
- Against spec: Preview should match course words and bare lemmas (870/874 intent). Mobile keyboards type U+2019 by default.
- Verdict: validated
- Rationale: validated

## Critic
- Challenge: Mobile keyboards (iOS/Android default) type U+2019, so this is the common input path, not tampering. I confirmed in code: _ARTICLES in enrich.py:40 and the article list in speech/vocab_review.py:_norm contain only ASCII ' forms, so l’eau skips stripping and course matching. Impact is real: wrong gender, duplicate personal card with the article baked in, shared cache poisoning. Fix is tiny.
- Holds up? Yes. Fixer scope: normalise U+2019 (and U+2018) to ASCII ' once at the start of strip_leading_article (enrich.py) and in _norm (speech/vocab_review.py) so lookup_slug, find_content_match and resolve_to_vocab all agree. Add a test for l’eau and L’été. Nothing else.
- Final verdict: validated

## Fix
strip_leading_article (app/content/enrich.py) and _norm (app/speech/vocab_review.py) normalise U+2019/U+2018 to ASCII ' first, so slug, course match and article stripping agree. Tests: tests/test_enrich.py::test_strip_leading_article, tests/test_personal_vocab.py::test_course_word_preview_matches_typed_variants_and_has_audio.
