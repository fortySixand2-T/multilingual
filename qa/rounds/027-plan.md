# QA round 027 — plan

- date: 2026-06-26
- app under test: backend :9000
- scope: B1 comprehension + writing content (PR #22, Phase 2 of B1 slice)

## Change surface (highest risk first)
PR #22 adds:
- `content/b1/comprehension/*.yaml` — 8 sets: 4 reading + 4 listening, each with 3 MCQ
  questions, `pass_threshold: 0.6`.
- `content/b1/writing/*.yaml` — 4 tasks: 2 Section A (80-150 words), 2 Section B
  (180-300 words), each with `target_vocab` referencing B1 vocab ids.
- `content/b1/audio/listen-b1-*.mp3` — 4 generated TTS clips for listening sets.

No exam/mock added yet (next PR, by design — do NOT file).

## Hypotheses (ranked)

| # | area | hypothesis | how to probe | persona |
|---|------|------------|--------------|---------|
| H1 | French correctness | B1 passages/scripts may have grammar errors (futur, conditionnel, subjonctif, agreement), wrong accents, or register issues | Read every passage, script, question, option, and explanation; verify grammar, accents, agreement, register | exam-crammer |
| H2 | MCQ answer integrity | An `answer` might not match any `options` entry exactly, or the answer might be wrong given the passage/script | For each Q, verify answer is in options list (exact string match) and is the correct answer from the passage | exam-crammer |
| H3 | MCQ explain accuracy | The `explain` quote might not actually appear in the passage/script, or might be misquoted | For each Q, verify the explain quote is a verbatim substring of the passage/script | exam-crammer |
| H4 | MCQ distractor quality | Distractors might be also-correct or absurdly implausible, undermining the test | Read each Q's wrong options against the passage; verify exactly one is correct | exam-crammer |
| H5 | Listening script-question alignment | Questions might ask about info not in the script, or the script might not support the answer | Cross-reference each listening Q with its script content | exam-crammer |
| H6 | Writing target_vocab resolution | `target_vocab` ids might not resolve to real B1 vocab words, causing loader crash | Call `load_tasks('content', 'b1')` and verify no WritingError | edge-case-breaker |
| H7 | Writing prompt coherence | Prompts might be unclear, mis-levelled, or have unreasonable word-count bounds for B1 | Review each prompt for task clarity, B1 appropriateness, and word-count feasibility | exam-crammer |
| H8 | Audio file resolution | `audio_ref` paths might not point to existing mp3 files | Verify each `audio_ref` resolves to an actual file in content/b1/audio/ | edge-case-breaker |
| H9 | Loader/sync integrity | `load_sets('content', 'b1')` or `load_tasks('content', 'b1')` might fail; comprehension-sync/assessment-sync might error | Run loaders programmatically; hit API endpoints | edge-case-breaker |
| H10 | Regression: A1/A2 unaffected | New B1 content might break existing level loading or test suite | Run `pytest -q`; verify A1/A2 comprehension/writing still loads | edge-case-breaker |
| H11 | Comprehension submit edge cases | Submitting wrong answer counts, empty answers, or duplicate submissions to B1 sets | POST /comprehension/sets/{b1_set_id}/submit with edge-case payloads | edge-case-breaker |

## Coverage gaps
- B1 comprehension submit flow (new sets, never tested against live API)
- B1 writing submit flow (new tasks, never tested against live API)
- B1 audio streaming endpoint `/comprehension/audio/{set_id}` for new listening sets

## Charters (per tester, with id blocks)

- `exam-crammer` (ids 403-412): Chase H1-H5, H7. Deep content review of all 8
  comprehension sets and 4 writing tasks. Verify every French passage, script, question,
  option, explanation, and prompt for correctness, B1 level-appropriateness, and MCQ
  integrity. This is the primary content-quality pass.

- `edge-case-breaker` (ids 413-422): Chase H6, H8-H11. Technical integration: verify
  loaders work, audio files exist, API endpoints return B1 data, test suite passes,
  A1/A2 regression check. Then poke B1 comprehension submit with edge-case payloads
  (empty answers, wrong answer count, double-submit).

## Don't re-file (already settled)
- 007 negative elapsed_seconds — rejected
- 001 invalid email — deferred
- 071 comprehension no-replay not enforced — deferred
- 180 comprehension feedback reveals answers — deferred
- 221 comprehension pass_threshold not shown — deferred
- 370 new writing tasks not synced to db — rejected
- 371 writing target_vocab off-theme for two tasks — rejected
- 394 level-filtered endpoints accept empty-string level — deferred
- 401 match-pairs en truncated vs vocab deck — deferred
- B1 has NO exam/mock — by design (next PR), do NOT file
- Drill / Writing / Speaking 503 with no provider — expected

## Outcome

| # | hypothesis | result | issue |
|---|------------|--------|-------|
| H1 | French correctness | refuted -- all grammar, accents, agreement, register correct | -- |
| H2 | MCQ answer integrity | refuted -- every answer is exact match in options and correct | -- |
| H3 | MCQ explain accuracy | refuted -- every explain quote is verbatim in passage/script | -- |
| H4 | MCQ distractor quality | refuted -- all distractors plausible but definitively wrong | -- |
| H5 | Listening script-question alignment | refuted -- all answers supported by script | -- |
| H6 | Writing target_vocab resolution | refuted -- all 17 vocab ids resolve in B1 deck | -- |
| H7 | Writing prompt coherence | refuted -- clear tasks, correct bounds, B1-appropriate | -- |
| H8 | Audio file resolution | refuted -- all 4 mp3 files exist (155-167 KB each) | -- |
| H9 | Loader/sync integrity | refuted -- 8 sets + 4 tasks load cleanly | -- |
| H10 | Regression: A1/A2 | refuted -- 143 tests pass, A1/A2 loaders unaffected | -- |
| H11 | Comprehension submit edge cases | refuted -- 404 on missing, 0-score on empty, no double-XP | -- |

**Verdict: clean round.** 0 issues filed. All 11 hypotheses refuted -- B1 content is sound.
