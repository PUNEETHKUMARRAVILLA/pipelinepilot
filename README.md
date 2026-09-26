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
- [ ] Week 3: Airflow failure → webhook → Slack report, no human action
- [ ] Week 4: evals, Streamlit trace viewer, demo video, results table below

## Results

| Scenario | Correct (of 5) | Avg seconds | Avg tool calls |
|---|---|---|---|
| _fill in after week 4_ | | | |

## Using real data later

Swap `generate_data.py` for a month of NYC TLC Yellow Taxi Parquet
(nyc.gov/tlc, "Trip Record Data") and map its columns to the ones in `staging`.
