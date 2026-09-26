# Dev log

Write 2-3 lines after each session: what you built, what broke, what you learned.

## Day 1 (2026-09-25)
- Set up uv + .venv, ran a healthy pipeline, confirmed all 6 failure scenarios break it on command.
- First agent run on schema_drift was WRONG with "high" confidence: it saw the source had `fare`
  instead of `fare_amount`, but blamed alias ordering in SQL it couldn't see, then "proved" it with its own query.
- Lesson: an agent is only as good as its tools. Confident tone is not evidence.

## Day 2 (2026-09-26)
- Added read-only tool `get_pipeline_code(step)` with an allow-list of 4 steps (can't read arbitrary files) + 2 tests.
- Re-ran schema_drift: correct root cause (upstream renamed `fare_amount` -> `fare`) and correct fix,
  in 5 tool calls / 14.8s (was 6 calls / 27.1s and wrong).
- Lesson: fix a wrong agent by giving it the missing information, not by scolding it in the prompt.
- Bugs found by accident: agent investigated a stale last_failure.json after a healthy run (made up a
  "duplicate column" cause), and printed an EMPTY report because thinking used up max_tokens=2000.
  Fixed: healthy run clears the failure file; max_tokens 16000; non-end_turn stops are reported, not blank.
- Manual check of all 6 scenarios: 6/6 correct root causes. But volume_drop's evidence cited two FAILED
  runs as the "normal 5000-row baseline" (one had 5800 rows). Right answer, wrong supporting fact.
- Lesson: grade the evidence, not just the conclusion.
