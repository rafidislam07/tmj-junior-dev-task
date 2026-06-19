# TMJ Quiet Tutor Task

## What I built
I built a short Python script that reads `sessions.csv` and `tutors.csv`, identifies tutors who have not run a session in 21 days or more, and outputs an actionable list.

## Output files
- `quiet_tutors.csv` — main action list of quiet tutors
- `no_session_tutors.csv` — tutors with no matched sessions
- `unmatched_sessions.csv` — session rows that could not be confidently matched to the tutor roster

## My approach
I treated 29 May 2026 as today, as stated in the brief. I matched tutor sessions to the roster by normalized name first, then used conservative fuzzy matching for messy name differences. I kept `tutor_id` in the final output because the brief required every quiet tutor to be identifiable by tutor ID.

## Result
The script found:
- 7 quiet tutors
- 0 tutors with no matched sessions
- 5 unmatched session rows

## Assumptions
I treated a tutor as quiet if they had a matched historical session but no session in the last 21 days. I did not silently merge uncertain rows; I wrote them to `unmatched_sessions.csv` for review.

## If I had more time
I would make `tutor_id` available directly in the session logs, add automated weekly reporting, and create a small review step for unmatched names.
