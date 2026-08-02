---
id: 572
title: TTS sanitizer `_clean` does not strip or normalize bare (non-Markdown) URLs
severity: low
area: speech
persona: edge-case-breaker
status: done
found: 2026-08-01
---

## Steps to reproduce
1. From the repo root, run:
   ```
   /tmp/tef312/bin/python -c "from app.ai.adapters.piper_adapter import _clean; print(repr(_clean('Voir https://exemple.fr/page pour plus.')))"
   ```

## Expected
Even though `examiner.md`/`conversation.md` now instruct the LLM to reply in
"plain spoken French only", the sanitizer is meant to be the safety net for when
the LLM doesn't fully comply. A bare URL dropped into a reply (no Markdown
wrapper) should ideally be stripped or replaced with something speakable, since
Piper will otherwise spell out the raw URL letter-by-letter/symbol-by-symbol
("h t t p s deux-points slash slash exemple point f r slash page") — a jarring,
confusing thing for a learner practicing listening comprehension to hear.

## Actual
```
_clean("Voir https://exemple.fr/page pour plus.")
-> 'Voir https://exemple.fr/page pour plus.'
```
The URL passes through completely untouched — `_MD_LINK` only unwraps
`[label](url)` syntax; there is no bare-URL regex at all.

## Notes
File: `app/ai/adapters/piper_adapter.py`. Lower severity than 571/570 because
the "plain spoken French only" prompt change (this same slice) reduces the odds
the LLM emits a raw URL in the first place — this is a defense-in-depth gap
rather than an observed live failure. Still worth a simple `\bhttps?://\S+\b`
strip given the sanitizer's stated purpose is being the safety net for
non-compliant LLM output.

## Triage
- Explanation: `_MD_LINK` only matches the `[label](url)` wrapper form and
  unwraps it to `label`; there's no independent bare-URL pattern in `_clean`,
  so a raw `https://...` token dropped into a reply (no Markdown syntax around
  it) is untouched by any of the four regex/translate steps. Reproduced
  directly: `_clean("Voir https://exemple.fr/page pour plus.")` →
  `'Voir https://exemple.fr/page pour plus.'` (URL intact).
- Against spec: `examiner.md`/`conversation.md` instruct "plain French prose
  only," which reduces (but per the plan's own framing, doesn't guarantee) the
  odds the LLM emits a raw link — so on a compliant turn this path isn't hit.
  The sanitizer's docstring nonetheless states its job is to be the
  belt-and-braces layer for exactly this kind of non-compliant output.
- Verdict: validated
- Rationale: Lower-severity duplicate mechanism of 571 (same jarring
  letter-by-letter URL read-out for a learner, just for a URL with no
  Markdown wrapper around it) — genuinely low-frequency since the prompt now
  actively discourages links, but the fix is a single added regex
  (`\bhttps?://\S+\b` strip or replacement) with no real risk to French text,
  so it's cheap enough to close alongside 571 rather than leave as a known gap.

## Critic
- Challenge: on its face this looks purely theoretical — a spoken French
  exam-practice conversation has no organic reason to contain a URL, the
  prompt explicitly forbids it, and the PM's own filing calls it
  "low-frequency" / "defense-in-depth gap rather than an observed live
  failure." That's a strong candidate for "not worth the churn": low
  severity, unlikely trigger, fixing a case that arguably shouldn't be
  encouraged (the app has no product surface where citing external URLs is
  the intended behavior in the first place).
- Holds up? Reproduced independently, matches the report exactly
  (`_clean("Voir https://exemple.fr/page pour plus.")` leaves the URL intact).
  On reachability: this app runs on a self-hosted local model, and asking a
  conversation partner for a resource/link ("un site pour pratiquer") is a
  plausible, in-scope learner question for a beginner-conversation app — a
  less-steerable local model answering with a real URL despite the
  instruction is a known failure mode, not a contrived one. Once the LLM
  emits any URL, the failure mode (Piper voicing/mangling raw URL syntax) is
  clearly a bad listener experience, and the fix is a single, low-risk regex
  with no downside for French text. Low severity is fair (per the PM's own
  filing) and the fix is cheap enough that severity being low doesn't tip it
  into "not worth doing" — it's a one-line, zero-risk addition to a sanitizer
  that already exists for exactly this purpose.
- Final verdict: validated

## Fix
Added a bare-URL regex (`_URL = re.compile(r"https?://\S+")`) to `app/ai/adapters/piper_adapter.py`, applied after the Markdown-link steps so it only catches URLs that were not already unwrapped from a `[label](url)`/truncated form. Covered by `test_strips_bare_url`.
