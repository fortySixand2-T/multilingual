# Speaking examiner staleness — 2026-10-19

Live box at 8e16e0f, `qwen2.5:7b-instruct-q4_K_M` on the GTX 1070.

## Method

- Called `AIRouter.run("examiner_roleplay")` directly with `cache=None`, so nothing was billed. Production doesn't cache this profile either.
- Same settings as live:
  - `max_tokens=220`
  - temperature 0.3
  - `mode=examiner`
  - the live opener prompt: `system_prompt + framing + _OPENER_DIRECTIVE`, with `_OPENER_CUE` as the user turn
- History was rebuilt the way `_recent_history` does it (last 3 turns).
- 272 sequential calls in total:
  - 29 topics × 8 openers
  - 4 sessions of 6 turns, each including one stall and one off-topic answer
  - 2 topics × 6 replies to the same learner turn

"Normalized" below means lowercased with punctuation stripped. Without it, "Bonjour!" and "Bonjour !" count as different openers.

## 1. Topic openers across sessions

| metric | LLM openers (before #120) | canned free-conversation opener |
|---|---|---|
| mean pairwise similarity (SequenceMatcher) | 0.67 | 1.00 |
| mean token Jaccard | 0.51 | 1.00 |
| exact-duplicate pairs (normalized) | 10% | 100% |
| near-duplicate pairs (similarity ≥ 0.85) | 27% | 100% |
| effective distinct variants per topic (of 8) | 4.1 (range 1.0–8.0) | 1 |
| start with "Bonjour ! Comment vas-tu ?" | 71% | — |
| median / max length | 22 / 44 words | 18 words |
| median / p90 latency | 1.67 s / 2.35 s | ~0 s |

**Effectively canned already:**
- `b1-b-ecrans`: 7 of 8 openers were word-for-word identical.
- `a2-a-bibliotheque`: all 8 fell in one near-duplicate cluster.
- `a2-b-transport` and `a2-b-marche` were close behind.

The variety that does exist is cosmetic: "Bonjour" + "Comment vas-tu ?" + a connector + the topic prompt reworded as a question.

## 2. Within a session (4 sessions × 6 turns)

- **Generic praise:** every turn (24/24) opens with short praise ("C'est super / génial / vrai…", "Très bien !", "Parfait !"). Every stall gets "Pas de problème !".
- **Praise is content-blind:** an off-topic answer was praised too.
- **Repeated questions:**
  - In `a2-b-transport`, the same follow-up question was asked verbatim in turns 4, 5 and 6 (trigram overlap 0.70).
  - In `a1-c-famille`, turn 6 re-asked something already answered in turn 1. Cause: the 3-turn history window.
- **Responding to the learner:** about 15 of 24 replies respond to something specific the learner said. The rest are praise followed by the next point from the topic's list.
- **No feedback:** none of the 24 turns gives the content or language feedback that `examiner.md` asks for.

## 3. The same learner turn in 6 fresh sessions

| topic | unique replies | mean similarity |
|---|---|---|
| a1-c-cafe | 6/6 | 0.45 |
| b1-b-ecrans | 6/6 | 0.75 |

At B1 the follow-up is close to deterministic: the same praise, the same paraphrase, and the same "Pourquoi ne nous parles-tu pas … ?"

## Quality problems found

1. **Register.**
   - The openers use tu in 195/232 samples, including 37/48 at B2. TEF examiners use vous.
   - 6 openers mix tu and vous in a single reply.
   - The prompt never specifies a register.
2. **Section A is played backwards.** The examiner tells the learner what to ask ("peux-tu me demander quel jour…") instead of answering in role. It gave no price for "Combien coûte le menu ?".
3. **Grammar errors learners would copy:** "quelles documents" (in all 8 bibliotheque openers), "Pourraient-vous", "liée au conduire".
4. **Invented details:** persona names, a "chaise longue", and openers drifting off-task.
5. **Length and level.**
   - Openers run up to 44 words, beyond the "one or two short sentences" instruction.
   - A2/B1 turns run 39–49 words.
   - The prompt never states the learner's CEFR level.
6. **No English, Markdown or emoji leaked** in any of the 272 outputs.

## Decisions

- **#120 replaces LLM topic openers with 5 authored variants per topic**, never repeating the line the learner heard last. That beats the measured variety (about 4 effective variants and 27% near-duplicates; random choice from 5 with no repeat gives 0% back-to-back repeats). It also removes the ~1.7 s opener latency, uses vous except in friend role-plays, and avoids every grammar issue above.
- **Follow-ups for the turn prompt (not done yet):**
  - React to one specific detail the learner said instead of opening with praise.
  - Never re-ask a question already asked or answered (a longer history window, or a list of questions already asked).
  - Fix the register to vous.
  - Make Section A answer in role.
  - State the learner's CEFR level.
  - Enforce shorter turns at A1/A2.
