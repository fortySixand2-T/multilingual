---
id: 1021
title: Preview of any course word returns audio_url null (no pronunciation clip), though the clip exists
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-10-31
---

## Steps to reproduce
Env: http://127.0.0.1:9302 (qa062-app), invite qa062-b.
1. POST /vocab/personal/preview for vélo, chat, chien, fils, hôtel, Noël, aujourd'hui, l'avion, cœur, sœur, grand-mère, docteur, professeur, ami, bureau, monsieur, examen, œuf.
2. GET /content/vocab -> same cards have audio "a1/audio/chat.mp3" etc.; GET /content/audio/a1/audio/chat.mp3 -> 200 (3514 bytes).

## Expected
audio_url present and playable (issue 874 expected "a playable clip"; 874's fix note says audio was already served from the card's clip).

## Actual
All 18 course-word previews: IPA correct and equal to /content/vocab, but `"audio_url": null`. Cause: content_vocab.data.audio is "" in the DB (confirmed via sqlite: chat -> "audio": ""); /content/vocab (app/content/api.py:246) derives `{level}/audio/{id}.mp3` when blank, but preview (personal_api.py:145) uses `d.get("audio")` only. The pronunciation panel therefore has no play button for exactly the words 874 was about.

## Notes
Fix: share the same fallback as api.py:246 in preview (needs level from match.level and d["id"]). Non-course words are unaffected (audio_url set, fetch 200).

## Triage
- Explanation: personal_api.py preview builds audio_url only from d.get('audio'), but content_vocab.data.audio is blank in the DB; api.py /content/vocab derives '{level}/audio/{id}.mp3' on the fly. Preview lacks that fallback. Confirmed in code at both sites.
- Against spec: 874: course-word preview should give a playable clip.
- Verdict: validated
- Rationale: validated

## Critic
- Challenge: Could be argued the audio is optional, but 874 explicitly promised a playable clip, and /content/vocab already derives the key when blank. Verified at both sites: personal_api.py:145 uses d.get('audio') only, api.py:246 falls back to '{level}/audio/{id}.mp3'. Fix is a one-line mirror, no model involvement.
- Holds up? Yes. Fixer scope: in preview use d.get('audio') or f'{match.level}/audio/{d["id"]}.mp3' (prefer extracting a tiny shared helper used by both api.py and preview rather than duplicating). Add a test that a course-word preview has non-null audio_url.
- Final verdict: validated

## Fix
New shared helper card_audio_key(level, card) in app/content/api.py used by /content/vocab and preview (app/content/personal_api.py), so course-word previews get the conventional <level>/audio/<id>.mp3 clip. Test: tests/test_personal_vocab.py::test_course_word_preview_matches_typed_variants_and_has_audio.
