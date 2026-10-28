---
id: 875
title: Piper IPA shows non-French values for some words (week-end wˈiːkˈɛnd, whisky wˈɪski, oignon onjˈɔ̃); French stress marks on every word
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-27
---

## Steps to reproduce
Env: http://127.0.0.1:9300 (qa060-app, real Piper). B=http://127.0.0.1:9300; T=<bearer token from POST /auth/signup, invite qa060-a>. Seed with: ssh rohith@10.0.0.54 docker exec -i qa060-app python - (sqlite3 on /app/data/tef.db).
1. POST preview for 'week-end', 'whisky', 'oignon', 'paquet' (add card then play), 'clef', 'yaourt'.

## Expected
French-phonology IPA (wikɛnd, wiski, ɔɲɔ̃, pakɛ), no ː length marks, no lexical-stress marks.

## Actual
'wˈiːkˈɛnd', 'wˈɪski' (English vowels/ː), 'onjˈɔ̃' (oignon should be ɔɲɔ̃), 'pakˈɛ', 'klˈe', 'jaˈuʁt'. Also compounds get a stress per part ('pˈøtˈɛtʁ'). Piper-equals-output data point per plan; file once. Learner sees ˈ on the last syllable of nearly every word, which is misleading for French (also H4).

## Triage
- Explanation: eSpeak phonemization via piper --debug: oignon -> onjˈɔ̃, fils/week-end/whisky anglicised or wrong, stress mark per word part. Piper output equals the IPA, so only a post-filter or override can change it.
- Against spec: PO: strip ˈ/ˌ for display and a small hand-curated override table (fils, oignon, cacahuète) is in scope; Lexique->IPA pipeline is NOT.
- Verdict: validated
- Rationale: Validated narrowed: (1) strip ˈ ˌ in the shared normalize function; (2) tiny override table keyed by normalized lemma (fils, oignon, cacahuète, plus week-end/whisky/yaourt only if trivially certain); overrides affect displayed IPA only. Note audio still says what eSpeak says, so overrides must not claim a pronunciation the clip contradicts badly; keep table to words where the clip is acceptable or flag it. ː removal for loanwords: only via table. Broader quality = next slice (Lexique).


## Critic
- Challenge: Quality of eSpeak output is the engine's behaviour; a curated override table is a hand-maintained data file that can contradict the audible clip (clip says oignon as eSpeak voices it).
- Holds up? Holds only in its narrow form: (1) stress-mark stripping lives in the shared normalize fn (shared with 882; implement once); (2) the override table stays tiny (fils, oignon, cacahuète, and only words with certain French IPA), keyed by normalized lemma, display-only, in one dict next to the normalize fn, no loader/pipeline/tsv. Do NOT add generic ː stripping or broad regex rewrites (would corrupt valid output). No week-end/whisky/yaourt unless trivially certain; anything else is the Lexique slice. Note the 64-char cap (873) applies after normalize.
- Final verdict: validated

## Fix
Display-only `IPA_OVERRIDES` (fils, oignon(s), cacahuète(s)) in `app/content/ipa.py`, applied by the shared `normalize_ipa`; no generic ː stripping, no loader. `tests/test_ipa.py` pins ~30 Wiktionary-style IPA and measures agreement (Piper raw: 22/35 exact after stress strip; misses cacahuète, fils, oignon).
- Files: `app/content/ipa.py`, `app/content/lookup.py`
- Tests: `tests/test_ipa.py::test_normalize_agrees_with_wiktionary_table`
