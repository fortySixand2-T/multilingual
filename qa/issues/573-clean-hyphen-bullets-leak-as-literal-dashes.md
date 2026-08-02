---
id: 573
title: TTS sanitizer `_clean` doesn't strip hyphen-bullet list markers (`- item`), only `* _ \` # > | ~`
severity: low
area: speech
persona: edge-case-breaker
status: done
found: 2026-08-01
---

## Steps to reproduce
1. From the repo root, run:
   ```
   /tmp/tef312/bin/python -c "from app.ai.adapters.piper_adapter import _clean; print(repr(_clean('- Bonjour\n- Ça va ?')))"
   ```

## Expected
`_MD_MARKS` is meant to strip Markdown formatting noise so it isn't voiced
literally. A hyphen-bullet list (very common Markdown list syntax, arguably more
common than `*`-bullets in LLM output) should be treated the same way as the
other markers — stripped, leaving just the list items collapsed onto the single
line (the module's own docstring says the whole point of collapsing to one line
is that Piper synthesizes per-line and a multi-line reply would cut off after the
first line, so bulleted lists are a realistic shape to hit here).

## Actual
```
_clean("- Bonjour\n- Ça va ?") -> '- Bonjour - Ça va ?'
```
The leading `-` on each line is not in `_MD_MARKS = re.compile(r"[*_\`#>|~]+")`, so
both dashes survive whitespace-collapse and would be voiced by Piper as literal
"tiret" or produce an odd pause before each list item.

## Notes
File: `app/ai/adapters/piper_adapter.py`. Simple fix: strip a `-` at the start of
a line before whitespace-collapse (order matters — must happen before the
single-line join since after collapsing there's no longer a reliable
"start-of-line" position; e.g. `re.sub(r"(?m)^-\s*", "", text)` run before
`" ".join(text.split())`). Lower severity since the prompt changes in this same
slice discourage Markdown formatting generally, but it's a plausible LLM habit
regardless of instructions.

## Triage
- Explanation: `_MD_MARKS = re.compile(r"[*_\`#>|~]+")` strips emphasis/heading/
  quote/table markers but the char class doesn't include `-`, so a leading
  hyphen-bullet on each line survives untouched, then whitespace-collapse
  (`" ".join(text.split())`) joins the lines, leaving `"- Bonjour - Ça va ?"`
  with the dashes now mid-sentence. Reproduced directly: `_clean("- Bonjour\n-
  Ça va ?")` → `'- Bonjour - Ça va ?'`.
- Against spec: prompts forbid bullet lists in spoken replies (defense-in-depth
  gap if the LLM doesn't comply, same framing as 570-572). Note per H1
  (confirmed refuted elsewhere in this round), `_clean` correctly *preserves*
  hyphens that are load-bearing for French (`qu'est-ce`, `peut-être`) — so any
  fix here must only strip a `-` at start-of-line, before the single-line
  join, not hyphens generally.
- Verdict: validated
- Rationale: Lowest-impact of the four (a mid-sentence "-" is more likely to
  read as a brief pause than a spoken word "tiret" on a neural TTS voice,
  unlike 571's character-by-character URL spelling), but it's a real,
  reachable gap in the sanitizer's own bullet-stripping intent and the fix
  (`re.sub(r"(?m)^-\s*", "", text)` before the line-join, as the reporter
  notes) is simple and low-risk to bundle with 570-572 rather than leave as a
  known gap.

## Critic
- Challenge: the prompt bans bullet lists outright, so on a compliant turn
  this never happens; and the PM's own filing rates the audible impact as
  the lowest of the four ("more likely to read as a brief pause than a
  spoken word"), which sounds close to imperceptible — arguably not worth
  even a one-line regex if the user-facing effect is just a slightly-longer
  pause in the TTS output.
- Holds up? No, this is the strongest-reachability issue of the four.
  Reproduced independently, matches the report exactly (`_clean("- Bonjour\n-
  Ça va ?")` → `'- Bonjour - Ça va ?'`). Unlike 571/572 (which need the model
  to invent a URL out of thematic context), a hyphen-bulleted list is a
  natural response shape any time the examiner gives multi-part
  content/language feedback ("Vous avez bien utilisé... Pensez aussi à...")
  — exactly the examiner's job per its own system prompt — and hyphen-lists
  are one of the single most common LLM formatting reflexes, including on
  local/smaller models that are worse at following "no bullet lists"
  instructions than frontier ones. On impact: the PM undersold it a bit —
  H1 in the round plan already confirms `_clean` must *preserve* hyphens in
  French elision (`qu'est-ce`, `peut-être`), so the sanitizer's whole design
  already draws a hyphens-are-meaningful-mid-word-only line; a leading `-`
  at start-of-line is unambiguously list-marker noise, not French text, so
  there's no ambiguity risk in stripping it, and it's inconsistent with the
  same regex already stripping `*`/`_`/backtick bullets. Real, easily
  reachable, cheap, unambiguous fix.
- Final verdict: validated

## Fix
Added `_LIST_BULLET = re.compile(r"(?m)^-\s*")`, applied before the final whitespace collapse (so start-of-line still means something) and before `_MD_MARKS`, stripping a leading `-` list marker per line while leaving mid-word hyphens (`qu'est-ce`, `peut-être`, `vas-y`) untouched since they are never at start-of-line. Covered by `test_strips_leading_hyphen_bullet_markers` and `test_hyphen_bullet_strip_preserves_french_elision_hyphens`.
