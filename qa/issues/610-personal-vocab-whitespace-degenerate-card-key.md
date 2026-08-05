---
id: 610
title: Whitespace-only `fr` produces a degenerate `uv:` card_key that collides across inputs
severity: medium
area: content
persona: edge-case-breaker
status: done
found: 2026-08-05
---

## Steps to reproduce
1. Sign up / log in as a user, get a bearer token.
2. `POST /vocab/personal` with `{"fr": " ", "en": "blank1"}` (a single space — passes
   the API's `min_length=1` validation on `fr`).
3. Observe the response.
4. `POST /vocab/personal` again with `{"fr": "   ", "en": "blank2"}` (three spaces —
   a different string, also passes validation).
5. Observe the response and compare to step 3.

## Expected
Either: whitespace-only `fr` is rejected with a 422 (nothing meaningful to store), or
each distinct whitespace string produces its own card. At minimum, two different raw
inputs should not silently merge into one shared, empty-identity card without any
signal to the caller.

## Actual
Both calls produce `card_key: "uv:"` (the `uv:` prefix with a **fully empty** slug),
and `fr` is stored as `""` (stripped to empty by `add_personal`, then `slugify("")`
also empty). The response for step 2:

```json
{"card":{"card_key":"uv:","fr":"","en":"blank1", ... },"added":true,"review_seeded":true}
```

The response for step 4 (different input, "   " vs " "):

```json
{"card":{"card_key":"uv:","fr":"","en":"blank1", ... },"added":false,"review_seeded":false}
```

Note `en` in the second response is still `"blank1"` — the three-space call is
silently treated as a duplicate of the one-space call (idempotency logic kicked in
on the degenerate empty slug) and its own `en: "blank2"` was discarded without any
indication to the caller. Any whitespace-only string, regardless of length or exact
content, collapses into this single `uv:` card per user. A learner who fat-fingers a
space into the "add word" box gets a nonsense empty-word card in their deck with no
error, and a second accidental whitespace-only submission silently vanishes into the
first rather than either erroring or creating a second entry.

## Notes
Root cause: `POST /vocab/personal` validates `fr` with `min_length=1` (which whitespace
satisfies), but `add_personal()` then does `fr = fr.strip()` before slugifying, so any
whitespace-only string strips to `""` and slugifies to `""`, producing card_key `uv:`
(app/content/personal.py `add_personal`/`slugify`/`personal_key`). This is different
from the previously-rejected "loose input" pattern (issues 290/300) because it isn't
just an oddly-shaped value being accepted — it's a real collision: unrelated raw inputs
map to the same stored identity and the second call's payload (`en`) is silently
dropped, with no distinguishing feature (like `fr`) surviving to tell the two apart.
A minimal fix would be validating `fr.strip()` is non-empty (422 otherwise), the same
protection min_length=1 was clearly meant to provide.


## Resolution (2026-08-05, round 049)
Fixed in `app/content/personal.py`: new `normalize_lemma()` strips a leading article and raises `EmptyLemmaError` when the word slugifies to nothing; the `POST /vocab/personal` handler maps that to **422**. No blank `uv:` card can be stored or seeded now. Regression test `test_add_rejects_degenerate_words_no_blank_card` (plus `test_add_strips_leading_article_like_preview`).
