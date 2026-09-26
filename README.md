# PipelinePilot

An AI on-call agent for data pipelines. When a pipeline run fails, it investigates with
read-only tools (logs, the source file, SQL on the warehouse) and reports the root cause
with a suggested fix for a human to approve.

## Scope (W5 + How)

| | |
|---|---|
| **Who** | On-call data engineer (user), a human approver, analysts who depend on the data |
| **What** | Agent that turns a failure event into: root cause, evidence, suggested fix, confidence |
| **When** | The moment a task or data-quality check fails (event-driven). Project: 4 weeks |
| **Where** | Local Mac: DuckDB file, Airflow in Docker, Claude via API, Slack for reports, GitHub for code |
| **Why** | On-call triage repeats the same checks; faster diagnosis means fresher, trusted data |
| **How** | Failure → webhook → agent loop (think → call tool → observe) → Slack report → human approves |

**In scope:** 1 pipeline, 6 failure types, 7 read-only tools, Slack report, traces, evals.
**Out of scope for now:** the agent changing data or code, streaming, cloud deploy, a polished UI.

## Quickstart (week 1-2)

```bash
brew install python@3.11 uv
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env            # add your ANTHROPIC_API_KEY

python -m pipeline.generate_data    # clean raw data
python -m pipeline.run              # healthy run (do this first: it sets the "normal" baseline)

python -m pipeline.break_it schema_drift
python -m pipeline.run              # fails, writes logs/last_failure.json
python -m agent.investigate         # the agent investigates

python -m pipeline.break_it reset   # back to clean
pytest -q                           # guardrail tests
```

Failure scenarios: `schema_drift`, `null_spike`, `duplicates`, `stale_data`, `type_change`, `volume_drop`.

## Layout

```
pipeline/  generate_data.py, run.py (ELT + checks), break_it.py (failure injection)
agent/     tools.py (read-only tools + guardrails), investigate.py (agent loop)
app/       week 3: FastAPI webhook + Slack + Airflow callback
evals/     week 4: accuracy / speed / cost
```

## Roadmap

- [x] Week 1: pipeline runs clean and breaks on command
- [x] Week 2: agent diagnoses all 6 scenarios from the CLI
- [x] Week 3: Airflow failure → webhook → Slack report, no human action
- [ ] Week 4: evals, Streamlit trace viewer, demo video, results table below

## Results

Pilot eval: 1 run per failure type, agent `claude-sonnet-5`, graded by a `claude-opus-5` judge
that compares the agent's ROOT CAUSE line with the injected truth (`python -m evals.run_evals --reps 1`).

| Scenario | Correct | Seconds | Tool calls | Cost |
|---|---|---|---|---|
| schema_drift | 1/1 | 11.2 | 4 | $0.024 |
| null_spike | 1/1 | 13.5 | 7 | $0.032 |
| duplicates | 1/1 | 19.9 | 8 | $0.046 |
| stale_data | 1/1 | 14.8 | 5 | $0.031 |
| type_change | 1/1 | 9.5 | 4 | $0.022 |
| volume_drop | 1/1 | 11.8 | 3 | $0.021 |

**6/6 correct, 9.5-19.9 s per diagnosis, about $0.03 per incident.** Six runs is a small sample
(95% CI 61-100%); `--reps 5` runs the full 30 (about $1). The judge only grades the root cause,
not whether each evidence bullet is true.

## Using real data later

Swap `generate_data.py` for a month of NYC TLC Yellow Taxi Parquet
(nyc.gov/tlc, "Trip Record Data") and map its columns to the ones in `staging`.
