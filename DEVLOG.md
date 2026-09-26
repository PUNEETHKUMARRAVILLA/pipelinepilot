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

## Day 2, afternoon (2026-09-26)
- Week 3 part 1: app/slack.py posts reports to Slack; app/webhook.py (FastAPI) takes POST /incident,
  replies 202 at once and runs the agent in a background task; run.py sends its failure event there.
- Now one command (break + run) ends with a correct report in #incidents, ~10-20s, no human step.
- Guardrails: the webhook rejects malformed events (422) and run_ids like "../x" (used in a file name);
  alerting has a 5s timeout and can never crash the pipeline.
- Lesson: don't change the data while the agent is still investigating. Evidence has to stay put.
- Week 3 part 2: Airflow 3 (Astro CLI, Docker) runs taxi_daily as 4 tasks. on_failure_callback records the
  failure and POSTs to host.docker.internal:8000. Duplicates run: quality_checks red, mart skipped,
  correct Slack report in 21.6s with no human step. Week 3 "done when" met.
- Gotchas: containers run in UTC (set TZ so pipeline_runs order stays right); Airflow run ids contain
  ":" and "+", which the agent's tools reject, so they are sanitised to [A-Za-z0-9_].
