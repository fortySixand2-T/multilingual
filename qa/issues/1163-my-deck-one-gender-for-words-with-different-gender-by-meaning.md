---
id: 1163
title: Dictionary lookup gives one gender for nouns whose gender depends on the meaning (vase, moule, physique, mode, pendule, aide, page, voile, poste)
severity: medium
area: content
persona: exam-crammer
status: done
found: 2026-11-12
---

## Steps to reproduce
1. POST /vocab/personal/preview for: un vase, une moule, la physique, le mode, le pendule, un aide, un page, la voile, le poste, le mousse.

## Expected
Gender matching the common/typed sense (le vase m, la physique f, la voile f sail / le voile m veil, le poste m), or a note that gender varies with the meaning.

## Actual
- "un vase"/"le vase" -> noun f "silt, mud, vase": vase (container) is masculine; f only for the rare "silt"
- "la physique" -> noun m "physique, physics" (physics is f)
- "le pendule" -> noun f "pendulum, pendulum clock" (pendulum m, clock la pendule f)
- "un aide" / "une aide" -> noun f "help, support, aide (person)" (aide person m/f)
- "une moule" -> noun m "mould, mold, mussel" (la moule = mussel is f)
- "la voile"/"le voile" -> noun m "veil, sail" (la voile = sail is f)
- "le mousse" / "la mousse" -> noun f "moss (the plant), bryophyte" (le mousse = ship's boy is m; foam sense missing)
- "un page" / "la page" -> noun f "page, page boy" (suffix rule)
- "le poste" -> f "post office" (course: la poste); the typed m ignored
The gloss merges senses of both genders under one gender, so the card teaches a wrong article for one of the senses. Typed article never corrects it.

## Notes
The dictionary table stores one gender per pos; senses of different gender are merged. Gender is presented with confidence (gender_source dictionary/table).

## Triage
- Explanation: Reproduced: le vase -> noun f 'silt, mud, vase'; un page -> f 'page, page boy' (suffix rule; page is in _AGE_FEM but the 'page boy' sense is m). TSV stores one gender per (word,pos), from the first entry's tags; senses of different gender are merged into one gloss, and resolve_gender puts table > suffix > dictionary, presented as authoritative.
- Against spec: Plan: gender resolved deterministically, table over model; no provision for gender-by-meaning words.
- Verdict: validated
- Rationale: Real, medium: the card teaches a wrong article for a common sense (un vase). FIX LOCATION: scripts/build_gloss_table.py (gender per entry; take the gender of the entry whose gloss leads, or 'mf' only for true epicene; override for ~20 known homographs) plus optionally runtime use of the typed article as a gender hint.

## Critic
- Challenge: Needs per-meaning gender data, i.e. hand-curated overrides for ~20 homographs; a design change.
- Holds up? Yes, but narrow. Verified vase -> noun f 'silt, mud, vase' in the TSV and fr_gender.tsv has no vase/physique row, so a common word teaches the wrong article. Scope: take gender from the entry that leads the gloss (rides with the 1146 rebuild) and add only the few highest-frequency rows (vase, physique) to the existing fr_gender.tsv; do not build a per-sense gender system.
- Final verdict: validated

## Fix
- `scripts/build_gender_table.py` + `app/content/data/fr_gender.tsv`: vase = m and physique = f rows. Per-sense gender is not modelled (critic scope).
