---
id: 561
title: Topic task card shows French prompt/points with zero support for absolute beginners
severity: low
area: web
persona: absolute-beginner
status: deferred
found: 2026-08-01
---

## Steps to reproduce
1. Sign up with invite code `friend-001`, land on Learn at level A1 (zero French).
2. Tap the "Speak" tile.
3. Tap either topic card in the picker (e.g. "S'inscrire à un cours").

## Expected
Per the persona's needs — zero French, easily confused, gives up on screens "in
French with no support" — a beginner picking a topic should get at least some
scaffold: an English gloss/translation of the prompt and points, a "what does this
mean" affordance, or a note like "these are real exam questions — don't worry
about understanding every word yet."

## Actual
The task card shows only French: title ("S'inscrire à un cours"), the full French
prompt paragraph ("Vous voulez vous inscrire à un cours de sport. Posez des
questions au secrétariat..."), and four French bullet points ("les jours et les
horaires", "le prix de l'inscription", ...). There is no translation, tooltip, or
any beginner support anywhere on the screen. An absolute-beginner persona with
zero French cannot understand what topic they just picked or what they're being
asked to talk about — this is exactly the "in French with no support" pattern the
persona is documented to bounce off of.

## Notes
This may be an intentional design choice (the topics are authentic TEF Expression
Orale exam prompts, and immersion/realism could be the point), so flagging as
low severity for triage rather than asserting it's wrong. If intentional, consider
at minimum a first-run tooltip or "topic = a scenario to talk about" explainer for
new/lower-level users, since the persona would otherwise likely abandon the screen
without understanding what "Section A" / the picker even means.

## Triage
- Explanation: Confirmed — read `content/a1/speaking/section-a-cours.yaml`
  and `section-a-restaurant.yaml` directly: title, `prompt`, and `points` are
  100% French, verbatim TEF Expression Orale task language, with no English
  field anywhere in the `SpeakingTopic` schema (`app/speech/topics.py:33-42`
  has `id, level, section, title, prompt, points` only — no gloss/translation
  field). `TopicPicker` (`web/src/screens/Speaking.tsx:153-215`) renders
  exactly those fields with no translation affordance, tooltip, or "what does
  this mean" support of any kind. The report is accurate.
- Against spec: `TEF_Platform_Technical_Plan.md` Phase 4 explicitly frames
  speaking practice as authentic TEF Expression Orale material and is
  silent on translation support. Phase 4 does describe the intended shape as
  **"level-gated (drills → conversation → examiner)"** — i.e. lower levels
  were meant to get a more scaffolded tier before full examiner-style
  practice (compare Phase 1's A1 drill tutor, explicitly speced as
  "scaffolded... English support allowed," `TEF_Platform_Technical_Plan.md`
  line 291). Checked the actual implementation: there is no "drills" tier in
  Speaking at all — `mode` is only `"examiner" | "conversation"`
  (`Speaking.tsx:8`), and `GET /speech/topics` (`app/speech/api.py:70-77`)
  filters topics by `level` but serves the *same* unscaffolded, full-French
  TEF exam prompt style at every level, A1 included. So the persona-friction
  the tester describes is real, and it does trace to a genuine gap between
  the spec's stated level-gating intent and what's shipped — but that gap
  (no scaffolded "drills" tier for speech) is a pre-existing hole in the
  whole Speech loop, not something this topic-bank PR introduced or could
  reasonably close: this PR's job was authoring/serving the topic bank to
  frame examiner/conversation sessions, not building a new speaking
  difficulty tier.
- Verdict: deferred
- Rationale: Real persona friction (self-flagged by the tester as possibly
  intentional, and I agree it's not a bug in this PR) — an absolute-beginner
  at genuine A1 gets zero scaffold on authentic French exam prompts, which
  does match the documented "in French with no support" pattern this persona
  bounces off of, and it does trace to a real spec gap (no scaffolded
  "drills" tier ever built for Speech, unlike A1 Drill's explicit "English
  support allowed"). But closing that gap is a scoped feature (a beginner
  tier for Speaking) well beyond this slice's topic-bank work, and low
  severity per the tester's own assessment. Worth a backlog item — a
  first-run "topic = a scenario to talk about" explainer or English gloss on
  `SpeakingTopic` — rather than blocking this PR.

## Critic
- Challenge: pm's own analysis leans hard toward "real gap" via the drills-tier
  comparison to A1 Drill Tutor - is that actually the right spec anchor, or is pm
  overreaching to justify treating a self-flagged "may be intentional" report as a
  confirmed spec violation? If the Plan is genuinely silent and the content is
  authentic-by-design (real TEF exam prompts), is there a defect here at all, or is
  this a feature request dressed as a bug?
- Holds up? Mostly, but the deferred call is right for a narrower reason than pm's.
  Confirmed the code facts independently: `SpeakingTopic` (app/speech/topics.py:33-42)
  has no gloss/translation field, `TopicPicker` renders raw French with zero scaffold,
  and Phase 1's A1 Drill Tutor spec line does say "English support allowed" for A1 -
  so pm's technical claims check out. But the drills-tier comparison is a stretch as
  "against spec" for *this* PR: Phase 4 (Speaking) explicitly frames the feature as
  authentic TEF Expression Orale material, and nothing in the Plan requires Speaking to
  replicate Phase 1's drill-tutor scaffolding pattern - different phase, different
  design intent, per pm's own admission it could be intentional. Where it does hold up:
  this is a real, cheap-to-fix persona-friction gap (a first-run explainer costs far
  less than a translation feature) that a genuine A1 learner would hit and bounce off
  of. But it's low severity, self-flagged as possibly-intentional by the tester, and
  scoped well beyond "topic bank + faster STT wiring" - building any beginner-support
  affordance is new UX surface, not a fix to something this PR broke. Deferring to a
  backlog item (not blocking this PR) is the right call; overturning to validated would
  push scope creep onto a slice that didn't create this gap.
- Final verdict: deferred
