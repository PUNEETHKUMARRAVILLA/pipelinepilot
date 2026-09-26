# app/: real time and the trace viewer

| File | What it does | Run |
|---|---|---|
| `webhook.py` | FastAPI server. `POST /incident` validates a failure event, replies `202 Accepted` at once, then runs the agent in a background task, saves the trace and posts the report to Slack. `GET /health` for liveness. | `uvicorn app.webhook:app --port 8000` |
| `slack.py` | Formats a trace as a Slack message and posts it to `SLACK_WEBHOOK_URL` (from `.env`). Never raises; returns `True`/`False`. | used by `webhook.py` |
| `trace_viewer.py` | Streamlit page: every saved incident step by step, plus eval results. Reads files only, so no API calls. | `streamlit run app/trace_viewer.py` |

Who calls the webhook:

- `python -m pipeline.run` on failure, at `AGENT_WEBHOOK_URL` (default `http://localhost:8000/incident`).
- Airflow's `on_failure_callback` in `airflow/dags/taxi_daily.py`, at
  `http://host.docker.internal:8000/incident` (set in `airflow/.env`), because Airflow runs in Docker.

If the server is down, the pipeline still fails normally and prints how to start it; alerting never
breaks the pipeline.
