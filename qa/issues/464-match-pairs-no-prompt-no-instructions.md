---
id: 464
title: match_pairs exercise type has no prompt field — beginner sees no instructions
severity: medium
area: content
persona: absolute-beginner
status: rejected
found: 2026-07-22
---

## Steps to reproduce
1. Sign up as a new user with invite code `friend-001`.
2. `GET /content/lessons/greetings-01` with a valid bearer token (remote:
   `https://rohith-alienware-17-r4.tail592ffa.ts.net`).
3. Inspect exercise `greetings-01.e4` (type `match_pairs`):

```json
{
  "id": "greetings-01.e4",
  "type": "match_pairs",
  "pairs": [
    ["bonjour", "hello"],
    ["salut", "hi"]
  ]
}
```

4. Note there is no `prompt` field — not even an empty string.
5. Repeat for `greetings-02`, `greetings-03`, `cafe-02`, `politeness-01` — none
   of the `match_pairs` exercises in any lesson have a prompt.

## Expected
A `match_pairs` exercise should include a `prompt` field giving the user an
instruction such as "Match each French word to its English meaning." Without any
instruction text, a brand-new learner cannot infer what action to take (drag, tap,
type?) or which direction to match.

## Actual
The `MatchPairsExercise` Pydantic model (`app/content/models.py` line 75-79) has NO
`prompt` field at all — not even an optional one with a default:

```python
class MatchPairsExercise(BaseModel):
    model_config = _Strict
    id: str
    type: Literal["match_pairs"]
    pairs: list[tuple[str, str]]
```

Every `match_pairs` exercise across all lessons (A1–B2) is served with no instruction
text. The first lesson a brand-new absolute beginner hits (greetings-01) ends with a
match_pairs exercise that is just two columns of words with no label, no task
description, and no hint about what to do.

By contrast, `ListenTypeExercise` has `prompt: str = ""` and `McqExercise` has a
required `prompt: str`. The omission in `MatchPairsExercise` is structural, not just
a content authoring gap.

## Notes
- Contrast with issue 230 (listen_type empty prompt in greetings-01, now fixed): that
  was a content-level omission where the field existed but was blank. Here the field
  does not exist in the model at all.
- `greetings-01.e4` is the 4th and final exercise of the very first lesson —
  a high-traffic point for absolute beginners with zero French.
- A typical fix would be: add `prompt: str = "Match each French word to its English
  meaning."` to `MatchPairsExercise` and optionally populate lesson YAML files. Even a
  static default in the model would give clients something to render.
- Found against live remote deployment:
  `https://rohith-alienware-17-r4.tail592ffa.ts.net`

## Triage
- Explanation: The HTTP tester saw no `prompt` field in the match_pairs API payload and inferred the learner sees no instructions. But MatchPairsExercise intentionally has no prompt field, and the web MatchPairs component (web/src/screens/Lesson.tsx:222) hardcodes the instruction "Match the pairs".
- Against spec: the rendered UI DOES show an instruction; the API-only view was misleading.
- Verdict: rejected
- Rationale: false positive from HTTP-only testing — a browser UI pass would not have flagged it. (Optional future nicety: per-exercise match_pairs prompts, but not a defect.)

## Critic
- Challenge: is a generic "Match the pairs" sufficient?
- Holds up? Yes — an adequate instruction is present; the "no instructions" claim is factually wrong for the rendered UI.
- Final verdict: rejected
