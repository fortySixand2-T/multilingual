---
id: 571
title: TTS sanitizer `_clean` leaves truncated Markdown link (unclosed paren) as raw `[label](url-fragment` text
severity: medium
area: speech
persona: edge-case-breaker
status: done
found: 2026-08-01
---

## Steps to reproduce
1. From the repo root, run:
   ```
   /tmp/tef312/bin/python -c "from app.ai.adapters.piper_adapter import _clean; print(repr(_clean(\"Regarde [le site](https://example.com/lo\")))"
   ```

## Expected
The LLM reply length is capped (per PR #62, "faster response — STT knobs + reply
cap"), which makes a reply getting truncated mid-Markdown-link a realistic,
foreseeable shape (`[label](https://ex...` cut off with no closing `)`). The
sanitizer should degrade gracefully here — at minimum not leave literal `[`, `]`,
`(` and a raw URL fragment for Piper to synthesize as spoken words/punctuation
("crochet, le site, parenthèse, h t t p s deux-points slash slash...").

## Actual
```
_clean("Regarde [le site](https://example.com/lo")
-> 'Regarde [le site](https://example.com/lo'
```
`_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")` requires a closing `)` to match,
so a truncated link is left completely untouched — brackets, parenthesis, and the
raw URL fragment all survive to be voiced by Piper.

## Notes
File: `app/ai/adapters/piper_adapter.py`. Since #62 (reply cap) and this slice
(#63, sanitizer) compose, a truncated-link reply is not a hypothetical edge case
but a plausible real occurrence. A defensive follow-up regex to catch/strip
incomplete `[...](...` sequences (or reordering: strip anything that looks like a
dangling markdown link opener even without the closing paren) would close this gap.
Related to issue 572 (bare URLs) and 573 (hyphen bullets) — same sanitizer, same
root cause: `_MD_LINK`/`_MD_MARKS` only catch well-formed Markdown, not malformed
or alternate forms.

## Triage
- Explanation: `_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")` requires both a
  closing `]` and a closing `)` to match; a reply truncated mid-URL leaves the
  opener `[label](https://...` with no closing paren, so the regex simply
  doesn't match and the whole fragment — brackets, parens, raw URL — passes
  through verbatim. Reproduced directly: `_clean("Regarde [le site]
  (https://example.com/lo")` → `'Regarde [le site](https://example.com/lo'`
  (byte-for-byte unstripped).
- Against spec: the prompts forbid Markdown/links in spoken replies, but PR #62
  (merged immediately before this slice, same speech pipeline) caps LLM reply
  length — which composes directly with this gap: a length cap makes truncation
  mid-token a normal occurrence, not a hypothetical, and truncation is exactly
  the shape `_MD_LINK` can't handle (no closing paren). The round plan
  (`qa/rounds/046-plan.md`) flagged this compositional risk explicitly before
  testing (H3) and it's confirmed.
- Verdict: validated
- Rationale: Highest-severity of the four sanitizer gaps — Piper would spell
  out a raw URL character-by-character/symbol-by-symbol mid-sentence
  ("crochet, le site, parenthèse, h t t p s deux-points slash slash..."),
  which is jarring for a listening-comprehension learner and, unlike 570/573,
  is plausible on *every* turn given the reply cap composes with any answer
  that happens to reference a link. Fix: strip a dangling `[...](` opener (with
  or without a closing paren) before/alongside `_MD_LINK`, e.g. also matching
  `\[[^\]]*\]\([^)]*$` for the truncated case.

## Critic
- Challenge: the PM's "plausible on every turn" framing overstates this badly.
  This is a TEF speaking-practice examiner/conversation partner discussing
  everyday topics — there is essentially no natural reason for it to emit a
  Markdown-formatted link at all, let alone one that happens to get truncated
  mid-URL by the 220-token cap (`examiner_max_tokens = 220`, generous for a
  2-4 sentence reply, so mid-token cutoffs are the exception, not the norm,
  for typical replies). This issue requires two independent low-probability
  events to align: (1) the model ignores the explicit "no Markdown... no
  links" instruction *and* invents a URL out of context, and (2) the reply
  cap lands exactly inside that URL. That reads like a stacked, largely
  theoretical scenario, not a realistic thing a learner will hit — closer to
  self-inflicted-by-prompt-injection than an ordinary conversation.
- Holds up? Reproduced independently and byte-for-byte matches the report —
  the mechanical gap is real. On likelihood: not "every turn," but not
  contrived either — a natural, learner-initiated trigger exists (a learner
  legitimately asking for a study resource, e.g. "des sites pour pratiquer le
  français ?", is exactly the kind of question this app's own topics would
  produce, and self-hosted local Ollama models are known to ignore
  format-only instructions and answer with a markdown-formatted link when
  asked for a resource). Given that base rate, and that this app runs on a
  local/smaller model rather than a tightly-steerable frontier one, a
  truncated-link leak is a real (if occasional) risk, not a hypothetical. The
  fix is a small, low-risk regex addition that also generalizes cleanly with
  572's bare-URL fix. I'll downgrade my confidence in "highest severity of
  the four" / "every turn" but the underlying gap and its worth-fixing status
  survive the challenge.
- Final verdict: validated

## Fix
Added `_MD_LINK_TRUNCATED` (`\[([^\]]+)\]\([^)]*$`) to `app/ai/adapters/piper_adapter.py`, applied right after `_MD_LINK`, to unwrap a dangling `[label](url-fragment` opener with no closing paren down to just `label`, dropping the partial URL. Covered by `test_strips_truncated_markdown_link_missing_closing_paren`.
