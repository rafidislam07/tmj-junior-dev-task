# TMJ Quiet Tutor Task

## What I built

A small Python script (`find_quiet_tutors.py`) that reads `sessions.csv` and `tutors.csv`, identifies tutors who have not run a session in 21 days or more, and produces CSV outputs a team member can act on.

## Output files

- `quiet_tutors.csv` — main action list of quiet tutors
- `no_session_tutors.csv` — tutors with no matched sessions
- `unmatched_sessions.csv` — session rows that could not be confidently matched to the tutor roster

## How to run

Run the script with the workspace's Python environment:

```bash
python find_quiet_tutors.py
```

## My approach

- Used the brief's date (29 May 2026) as the reference "today".
- Matched session rows to the tutor roster using normalized names first, then conservative fuzzy matching for messy name differences.
- Preserved `tutor_id` in outputs so each quiet tutor is identifiable.

## Result

- Quiet tutors found: **7**
- Tutors with no matched sessions: **0**
- Unmatched session rows: **5**

## Assumptions

- A tutor is considered "quiet" if they had at least one historical matched session but none in the last 21 days.
- Uncertain matches are not merged silently; they are written to `unmatched_sessions.csv` for manual review.

## Future improvements

- Surface `tutor_id` directly in session logs to simplify matching.
- Add automated weekly reporting (email or dashboard).
- Add a small interactive review workflow for unmatched names to reduce manual review time.


