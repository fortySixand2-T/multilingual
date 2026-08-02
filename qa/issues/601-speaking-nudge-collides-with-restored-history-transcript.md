---
id: 601
title: Nudge text "review words from your last conversation" is confusing because the exact same conversation is already rendered inline above it
severity: medium
area: web
persona: returning-learner
status: done
found: 2026-08-02
---

## Steps to reproduce
1. Seed one prior `speech_turns` row for a user with a `session_id` (e.g.
   transcript "Bonjour, comment allez-vous?" / reply "Bonjour! Ca va bien, merci.
   Et vous?").
2. Log in as that user and open `/speaking` fresh (first load of the tab).
3. Look at the rendered page top-to-bottom.

## Expected
A returning learner should be able to tell, at a glance, what the nudge
"Review words from your last conversation" refers to versus what's already on
screen. If the last conversation's transcript is already visibly restored on the
page, the nudge's wording should make clear it's offering something *additional*
(reviewing the vocabulary from it), not duplicate/contradict the already-visible
content.

## Actual
On first load, the page renders (top to bottom): the topic picker, then the nudge
box "Review words from your last conversation" / "Not now", and immediately below
it the *exact same* prior conversation's transcript already restored and displayed
as "You said: Bonjour, comment allez-vous?" / "Examiner: Bonjour! Ca va bien,
merci. Et vous?" (this comes from the pre-existing `GET /speech/history` restore,
unrelated to this slice but co-rendered on the same screen). A learner reading top
to bottom sees: a card telling them to "review words from your last conversation,"
then, right underneath, that exact last conversation already sitting there in full.
It reads like the nudge is offering to show them something they can already see,
which is confusing about what clicking the nudge actually adds (it adds the
conversation's vocabulary to their review deck — the wording doesn't hint that the
action is "add to review deck" vs. "reread this transcript again").

## Notes
- This isn't literally the H9 scenario as scoped (nudge + end-of-conversation
  debrief card) since the end-of-conversation card never had a chance to appear
  (STT is unavailable in this environment, so no real turn could be submitted this
  session) — this is a *different* co-visibility collision: nudge + restored
  history transcript, which occurs on essentially every fresh page load for a
  returning learner with a prior session, so it is likely to be a very common
  first impression of this feature.
- Suggest a small copy/layout tweak: either move the nudge below the visible
  history transcript, or make the nudge's blurb explicit that clicking it adds the
  vocabulary from what's shown below to the review deck.

## Triage
- Explanation: reproduced live. Seeded a fresh test user (`user_id=177`,
  one `speech_turns` row, `session_id=prior-triage-1`) and loaded `/speaking`
  in Chrome. Confirmed by screenshot: the page renders, top to bottom, the
  topic picker, then the nudge ("Review words from your last conversation" /
  "Not now"), then immediately below it the *same* turn restored via
  `GET /speech/history` ("You said: Bonjour, comment allez-vous?" /
  "Examiner: Bonjour! Ca va bien, merci. Et vous?"). `GET /speech/history`
  (`app/speech/api.py:310-336`) returns *all* of a user's turns regardless of
  session, unscoped and pre-existing (not part of this slice), and it's
  rendered directly under the nudge in `Speaking.tsx` (lines 150-182). Because
  a learner typically only has one recent conversation, the nudge and the
  full restored transcript of that exact conversation are co-visible on
  essentially every fresh load for a returning learner — the feature's
  explicit target persona.
- Against spec: unspecified for this exact interaction — the round plan
  flagged the general risk class (H9, nudge + end-of-conversation
  co-visibility) but not this specific nudge + history-restore collision.
  The nudge's blurb ("From your last conversation — add any to your review
  deck") doesn't reference or distinguish itself from the already-visible
  transcript, so nothing in the current copy/layout resolves the ambiguity
  the tester describes.
- Verdict: validated
- Rationale: user impact — a returning learner's first impression of this
  feature is a nudge that appears to duplicate/contradict content already on
  screen, obscuring that the nudge's real action is "add this conversation's
  vocabulary to the review deck," not "reread the transcript." Low
  implementation cost to resolve (copy or ordering change) relative to the
  confusion it causes for the primary target persona of this slice.


## Resolution
Fixed with a copy tweak in `web/src/screens/Speaking.tsx`: the prior-session nudge label is now "+ Add vocab from your last conversation" (was "Review words from your last conversation"), making the action — add vocabulary to the SRS review deck — clear and distinct from the restored transcript shown below it, rather than reading like "re-read".
