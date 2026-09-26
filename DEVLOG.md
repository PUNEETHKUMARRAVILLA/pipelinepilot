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
