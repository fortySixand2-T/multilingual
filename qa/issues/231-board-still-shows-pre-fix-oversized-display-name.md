---
id: 231
title: Board still serves a 20,000-char display_name from pre-fix data
severity: medium
area: progress
persona: absolute-beginner
status: done
found: 2026-06-21
---

## Steps to reproduce
1. Sign up and complete a lesson so your user appears on the board.
2. `GET /progress/board` with a valid bearer token.
3. Inspect the response for user_id 28.

## Expected
Every display_name on the board is at most 80 characters (the cap added in issue 130).
The board response is compact and renders quickly on a phone.

## Actual
User 28's display_name is 20,000 characters of "X". The total board JSON response is
~23 KB, with ~20 KB from this single name. Issue 130 added a `max_length=80` validation
on signup, but existing rows created before the fix were not truncated. The fix
prevented new oversized names but left the old data in place.

## Notes
The fix for issue 130 should have included a data migration to truncate existing
display_name values to the new 80-char limit, or the board endpoint should truncate
at read time. As a beginner on a phone, the bloated board response is slow and the UI
would be broken by the giant name. A one-line `UPDATE users SET display_name =
substr(display_name, 1, 80) WHERE length(display_name) > 80` would clean it up.

## Triage
- Explanation: Confirmed. Issue 130 added a `max_length=80` Pydantic constraint on the signup body (`app/api/auth.py` line 38), preventing new oversized display names. However, the DB column is `String(120)` (`app/users/models.py` line 18) and no data migration was run to truncate existing rows. The board endpoint (`app/progress/api.py` line 135) reads `u.display_name` directly with no truncation. Any pre-fix user with a long display_name still has it served as-is, bloating the board JSON response for all users.
- Against spec: The spec (R11) emphasizes the group progress board as a motivation layer. A 20KB display_name in the board response degrades the experience for every user on every board load. The fix for issue 130 was incomplete -- it closed the write path but did not clean existing data.
- Verdict: validated
- Rationale: Every board request serves ~20KB of junk data to all users due to one pre-fix row. On mobile this is noticeable latency and the UI would render a visually broken leaderboard. Fix requires either a data migration to truncate existing rows or a read-time truncation in the board endpoint (or both).

## Critic
- Challenge: This is test data, not a production scenario. User 28 with a 20,000-char name was created during QA testing before the fix for issue 130. In a real deployment, (a) the DB would be fresh with no pre-fix data, and (b) the String(120) column would enforce length in any real database engine (Postgres, MySQL). SQLite is the dev/test engine and does not enforce column length, which is why this artifact exists. The "fix" would be a data migration that only matters for SQLite test databases. This is self-inflicted test pollution, not a bug real users would hit.
- Holds up? Partially. The challenge is strong: this IS test data in a SQLite dev database, and a production Postgres deploy would enforce String(120) at the DB level. However, the platform spec says it is self-hosted, and the default config uses SQLite. If the deployment target includes SQLite (which it currently does), the write-path-only fix for issue 130 is genuinely incomplete. A defense-in-depth read-time truncation in the board endpoint would cost one line and protect against any DB engine that does not enforce column length. The fix scope matters: a data migration is overkill, but a read-time truncation is cheap and correct.
- Final verdict: validated
- Rationale: The default deployment uses SQLite, which does not enforce String(120). The write-path cap from issue 130 is necessary but insufficient -- a read-time truncation in the board endpoint is a one-line defense-in-depth fix that protects all users regardless of DB engine or legacy data.

Fix: Read-time truncation `[:80]` on display_name in board endpoint (`app/progress/api.py`); data migration `0010_truncate_display_names.py` to clean existing rows.
