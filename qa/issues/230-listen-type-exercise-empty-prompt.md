---
id: 230
title: listen_type exercise in greetings-01 has empty prompt -- beginner gets no instruction
severity: medium
area: content
persona: absolute-beginner
status: done
found: 2026-06-21
---

## Steps to reproduce
1. Sign up as a new user with invite code `friend-001`.
2. `GET /content/lessons/greetings-01` with a valid bearer token.
3. Inspect exercise `greetings-01.e3` in the response.

## Expected
The listen_type exercise should have a prompt telling the user what to do, e.g.
"Type the word you hear." (as numbers-01.e2 does: `"prompt": "Type the number you hear."`).

## Actual
`greetings-01.e3` returns `"prompt": ""` (empty string). The source YAML
(`content/a1/lessons/greetings-01.yaml` line 23) has no `prompt` field at all for
this exercise. A beginner sees an audio player and a text input with zero instruction
on what to type.

## Notes
This is a content data issue, not a code bug. The other listen_type exercise
(numbers-01.e2) correctly has `prompt: "Type the number you hear."` -- so the schema
supports it, but greetings-01.e3 simply omits it. For a zero-French absolute beginner,
this is the very first lesson and the missing instruction makes the exercise
incomprehensible. Severity is medium because the exercise is unusable without context.

## Triage
- Explanation: Confirmed. `content/a1/lessons/greetings-01.yaml` exercise e3 (listen_type) has no `prompt` field. The content API (`app/content/api.py` line 122) returns `lesson.data` verbatim from the DB, which mirrors the YAML. The comparable exercise `numbers-01.e2` has `prompt: "Type the number you hear."` -- the field is supported but simply missing from this one exercise. Since greetings-01 is the very first lesson for absolute beginners, a listen_type exercise with no instruction text leaves the user staring at an audio player and text input with no idea what to do.
- Against spec: AC1.1 says content is authored as YAML and synced. The content schema supports prompt fields on listen_type exercises. This is a content authoring gap, not a code bug, but it violates the spirit of Phase 1 which is meant to "carry learners through months 1-3" as absolute beginners.
- Verdict: validated
- Rationale: Content defect in the first lesson a beginner encounters. An absolute-beginner persona with zero French cannot infer what to type from an audio clip alone. One-line YAML fix: add `prompt: "Type the word you hear."` to greetings-01.e3.

## Critic
- Challenge: The Pydantic model `ListenTypeExercise` defines `prompt: str = ""` -- an empty string is the explicit default, meaning the schema treats a missing prompt as valid. The exercise type is "listen_type" which is self-describing: you listen, you type. A frontend could render a generic instruction for any listen_type exercise missing a prompt (e.g., "Type what you hear"). This is arguably a frontend concern, not a content bug. Furthermore, the exercise still functions -- the audio plays, the text input accepts input, and the answer is validated correctly.
- Holds up? No. The challenge fails on the persona test. This is the very first lesson for absolute beginners with zero French. The platform is self-hosted with no guaranteed frontend -- the API is the product surface, and it returns an empty prompt. Relying on a hypothetical frontend to paper over missing content is not a fix. The comparable exercise (numbers-01.e2) has a prompt, proving the content authors intended prompts on listen_type exercises. The omission is an authoring oversight, not a design choice.
- Final verdict: validated
- Rationale: Content gap in lesson one, the highest-traffic lesson for the target persona. The model supports prompts, the sibling exercise has one, this one does not. One-line YAML fix with zero risk.

Fix: Added `prompt: "Type the word you hear."` to greetings-01.e3 in `content/a1/lessons/greetings-01.yaml`.
