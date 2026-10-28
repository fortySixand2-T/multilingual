---
id: 874
title: Preview of a course-vocab word shows no IPA and often no audio (vélo, chat, chien, fils, hôtel...)
severity: medium
area: content
persona: edge-case-breaker
status: deferred
found: 2026-10-27
---

## Steps to reproduce
Env: http://127.0.0.1:9300 (qa060-app, real Piper). B=http://127.0.0.1:9300; T=<bearer token from POST /auth/signup, invite qa060-a>. Seed with: ssh rohith@10.0.0.54 docker exec -i qa060-app python - (sqlite3 on /app/data/tef.db).
1. POST preview {"word":"vélo"} (also chat, chien, bureau, fils, monsieur, examen, hôtel, Noël, aujourd'hui, l'avion, cœur, œuf, sœur, grand-mère).

## Expected
Same pronunciation panel as other words: Piper IPA and a playable clip.

## Actual
{"enrichment":{"fr":"vélo",...,"ipa":"","audio_url":null},"in_course":"a2"} - no IPA and no audio_url for these (content_vocab rows have audio:""; 0 of 1852 rows have ipa). A learner checking the pronunciation of a basic word gets nothing, inconsistent with non-course words like 'sur' that get both. Particularly bad since users report pronunciation issues.

## Triage
- Explanation: preview short-circuits for words found in content_vocab (in_course) and returns ipa '' and audio_url null (personal_api.py ~line 134); content_vocab has no IPA.
- Against spec: Pronunciation is the core of the complaint; course words are the most common words a learner checks. Not a deferred-pipeline item.
- Verdict: validated
- Rationale: In scope, minimal: for in_course words, also run the normal lookup/voicing path (same Piper IPA + clip, same override table) and return it alongside in_course; do not add a Lexique pipeline or bulk-populate content_vocab (next slice). If Piper latency per first lookup is a concern, lazy-derive on first preview and cache in vocab_lookup.


## Critic
- Challenge: The in_course branch is deliberately 'no model call'; routing it through the normal lookup spends LLM + Piper budget and creates vocab_lookup rows for words the learner already studies. The user's complaint was a personal word (cacahuetes), not course words; the course card already has its own gen_audio clip live (audio empty only in the scratch container); an absent IPA line is not wrong IPA, it is just absent. Also adds ipa from a different engine than the course clip.
- Holds up? Overturned on scope: nothing nonsensical is shown, the course branch is not a cause of the reported bug, and the fix adds cost/latency to a path designed to be free and exposes still-imperfect eSpeak IPA on the most common words before the Lexique slice (same reasoning the PM used to defer 883). Defer to the Lexique/IPA slice.
- Final verdict: deferred
