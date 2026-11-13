---
id: 1192
title: Wiktionary (CC BY-SA 4.0) attribution not shown anywhere a learner or user can see; Lexique not credited either
severity: medium
area: other
persona: absolute-beginner
status: done
found: 2026-11-12
---

## Steps to reproduce
1. Browse the app UI: My deck, lookup preview, Learn, footer/header, no About/Credits page exists. Dictionary meanings from fr_gloss.tsv.gz (built from kaikki.org's English Wiktionary extract) appear in My deck previews and saved cards.
2. `grep -rniE "wiktionary|CC BY|lexique" web/src README.md docs` : no hits in web/src or README.md.

## Expected
CC BY-SA 4.0 requires attribution (credit to Wiktionary, link to the licence, indication of changes) for the derived data; and share-alike on the adapted gloss table. Expect an About/Credits page or a footer note ("Meanings from Wiktionary, CC BY-SA 4.0; gender/frequency data from Lexique 3") plus a licence/attribution file in the repo for app/content/data/fr_gloss.tsv.gz.

## Actual
Attribution exists only in developer comments: app/content/dictionary.py line 7 and scripts/build_gloss_table.py line 10 ("Wiktionary is CC BY-SA 4.0"), and docs/anki-vocab-plan.md mentions the Anki deck being CC-BY-SA. Nothing in the UI, README, or beside the data file. Lexique (source of gender/frequency) is likewise credited only in code docstrings, so the new Wiktionary data is treated the same as Lexique but both are unattributed to users.

## Notes
Compliance gap rather than a UX bug. Suggested minimal fix: an "About / Credits" link in the footer or My deck card, and a NOTICE/ATTRIBUTION.md next to the data file.

## Triage
- Explanation: Confirmed: README.md and web/src contain no mention of Wiktionary or Lexique; credit exists only in code comments (dictionary.py, build_gloss_table.py docstring) while fr_gloss.tsv.gz is derived data shown to learners.
- Against spec: Wiktionary text is CC BY-SA 4.0: attribution, licence link, indication of changes and share-alike on the derived table are required; the plan treats third-party data credit as expected.
- Verdict: validated
- Rationale: Real compliance gap, medium, cheap. FIX LOCATION: UI/docs: About/Credits link or footer note, plus NOTICE/ATTRIBUTION file beside app/content/data (also check Lexique's licence terms).

## Critic
- Challenge: Is it a bug rather than compliance paperwork?
- Holds up? Yes. CC BY-SA 4.0 requires attribution, licence link and indication of changes; none is visible in UI/README, only code comments. A real legal gap, cheap to close: footer/credits line plus a NOTICE file next to the data; also check Lexique's licence terms.
- Final verdict: validated

## Fix
- `web/src/Credits.tsx` (footer on every screen, credits Wiktionary and Lexique, says the data was adapted, links CC BY-SA 4.0), `app/content/data/NOTICE.md` (attribution, changes made, share-alike) and a Credits section in `README.md`. Test: `web/src/Credits.test.tsx`.
