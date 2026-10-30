---
id: 920
title: IPA of "bon appétit" and "soins à domicile" carries an eSpeak liaison artifact (bɔ̃n, swɛ̃z)
severity: low
area: content
persona: edge-case-breaker
status: done
found: 2026-10-29
---

## Steps to reproduce
1. `GET /content/vocab` (any user token) on the QA app (:9301) and read the `ipa` of `bon_appetit` (a1) and `soins_domicile` (b2).
2. Compare with the Lexique word-by-word join and with standard French (Wiktionary).
3. On the box: `printf 'bon appétit\n' | docker exec -i qa061-app piper --model /app/voices/fr_FR-upmc-medium.onnx --output_file /dev/null --debug` prints `ids: bˈɔ̃n apetˈi`.

## Expected
Liaison is shown without losing the nasal vowel, or not at all: `bɔ̃ napeti` (bɔ̃.na.pe.ti). For "soins à domicile" no liaison between a plural noun and "à" (`swɛ̃ a domisil`).

## Actual
The script keeps Piper's phrase phonemes when Lexique and Piper disagree (build_vocab_ipa.py `resolve`), and those phonemes include eSpeak artifacts:

| word | current IPA | correct IPA | evidence |
|---|---|---|---|
| bon appétit (a1 `bon_appetit`) | bɔ̃n apeti | bɔ̃ napeti | Piper `bˈɔ̃n apetˈi` copied as-is; "bon" + n is a denasalised /bɔn/ ("bonne"); Lexique join gives `bɔ̃ apeti` |
| soins à domicile (b2 `soins_domicile`) | swɛ̃z a domisil | swɛ̃ a domisil | Lexique join `swɛ̃ a domisil`; liaison after plural noun before "à" is not made in standard French |

## Notes
Neither is in `REVIEWED`. "bon appétit" is an a1 phrase, so a beginner sees a wrong nasal. Scan for other Piper-sourced phrases: only these two are clearly wrong (`les États-Unis`, `des acquis`, `en œuvre/évidence` liaisons are correct).


## Triage
- Explanation: build_vocab_ipa.py keeps Piper phrase phonemes on Lexique/Piper disagreement; Piper emits eSpeak liaison artifacts. Confirmed in content: restaurant.yaml bɔ̃n apeti, sante.yaml swɛ̃z a domisil.
- Against spec: Checked IPA is the feature's stated purpose.
- Verdict: validated
- Rationale: Two wrong IPA strings shown to learners, one on an A1 phrase. Add to REVIEWED (bɔ̃ napeti, swɛ̃ a domisil).

## Critic
- Challenge: Cosmetic IPA.
- Holds up? Yes: bɔ̃n on an A1 phrase is a wrong nasal, checked IPA is the feature's purpose; REVIEWED entries are trivial.
- Final verdict: validated

## Fix
Set bɔ̃ napeti / swɛ̃ a domisil in the vocab YAML and added both to REVIEWED in scripts/build_vocab_ipa.py.
