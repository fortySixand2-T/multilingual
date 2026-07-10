---
id: 452
title: test_drill_endpoint_derives_level_from_lesson omits a2 and b2 HTTP coverage
severity: low
area: tutor
persona: edge-case-breaker
status: fixed
found: 2026-07-06
---

## Steps to reproduce
1. Open `tests/test_tutor_levelgate.py`.
2. Find `_setup()` (lines 35-40):
   ```python
   await sync_bundle(s, load_content(CONTENT_ROOT, "a1"))
   await sync_bundle(s, load_content(CONTENT_ROOT, "b1"))  # for level-derivation test
   ```
   Note that a2 and b2 content is NOT loaded into the test database.
3. Find `test_drill_endpoint_derives_level_from_lesson` (line 183):
   ```python
   assert client.post("/tutor/drill", json={"lesson_id": "travail-b1-01"}).status_code == 200
   assert fake.calls[-1]["profile"] == "drill_b1"
   assert client.post("/tutor/drill", json={"lesson_id": "greetings-01"}).status_code == 200
   assert fake.calls[-1]["profile"] == "drill_a1"
   ```
   Only a1 and b1 lessons are exercised. a2 and b2 are absent from both the
   test DB setup and the HTTP-level assertions.
4. Run the tests — they pass, but a2 and b2 level-derivation via the HTTP
   endpoint is untested.

## Expected
The `test_drill_endpoint_derives_level_from_lesson` test (or a companion test)
should also:
- Load a2 and b2 content into the test database (`sync_bundle` for "a2" and "b2").
- POST a known a2 lesson (e.g. `cuisine-a2-01`) and assert
  `fake.calls[-1]["profile"] == "drill_a2"`.
- POST a known b2 lesson (e.g. `sciences-b2-01`) and assert
  `fake.calls[-1]["profile"] == "drill_b2"`.

This is the HTTP-level proof that the level-derivation feature actually routes
a2 and b2 lessons through the correct AI profiles end-to-end.

## Actual
Only a1 and b1 are covered at the HTTP endpoint level. The a2 and b2 profiles
(`drill_a2`, `drill_b2`) — which are part of the advertised feature — are
validated only by the unit-level `test_every_level_has_a_scaffolded_gated_prompt`
test (which mocks the DB entirely). If the content YAML for a2/b2 were missing a
`level:` field, or if the lesson were looked up by a different key in the API,
the tests would still pass while the feature silently fails for real users.

## Notes
- Severity: medium — the feature works live (confirmed by manual `curl` returning
  503 for `sciences-b2-01`), but the gap means a regression in a2/b2 routing
  would not be caught by CI.
- Fix: add `await sync_bundle(s, load_content(CONTENT_ROOT, "a2"))` and
  `await sync_bundle(s, load_content(CONTENT_ROOT, "b2"))` to `_setup()`, then
  extend `test_drill_endpoint_derives_level_from_lesson` to assert a2/b2 profiles.

## Triage

- status: validated
- severity: medium
- investigator: qa-pm

### Finding
Confirmed: `_setup()` in `test_tutor_levelgate.py` loads only a1 and b1 content, and `test_drill_endpoint_derives_level_from_lesson` asserts only `drill_b1` and `drill_a1` profiles at the HTTP level. Both `content/a2/lessons/` (e.g. `cuisine-a2-01.yaml`) and `content/b2/lessons/` exist on disk and are loadable via `sync_bundle`. The unit test `test_every_level_has_a_scaffolded_gated_prompt` mocks the DB entirely and does not exercise the `lesson.level` DB field or the HTTP routing path, so a broken `level:` field in a2/b2 YAML or a lookup-key mismatch in the API would pass CI silently. The gap is a real regression blind spot for a shipped multi-level feature.

## Critic

- status: deferred
- critic: qa-critic

### Assessment
The PM's primary stated risk — "a missing level: field in content YAML" — is not actually possible. The `Lesson` Pydantic model uses `extra="forbid"` and has no `level` field; level is never in lesson YAML, it comes exclusively from `path.yaml` → `bundle.path.level` → `sync_bundle` writing it to the `ContentLesson.level` DB column. The `content/a2/path.yaml` and `content/b2/path.yaml` both declare the correct level value. The only real slip-through scenario is a bug in `sync_bundle` writing the wrong level to the DB column — but that would equally break the a1/b1 coverage already in the test. The derivation logic in `api.py` is completely level-agnostic (`Tutor(ai_router, level=lesson.level)`), and adding a2/b2 HTTP coverage would test the same generic dict lookup, not any a2/b2-specific code path. The gap is real but the probability of it catching a regression that a1/b1 coverage misses is very low. Severity `medium` overstates the risk. This is legitimate test hygiene and worth adding eventually, but it does not meet the bar for an urgent validated fix — consistent with how issue 450 was handled. Verdict: deferred.
