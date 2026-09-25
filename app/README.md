# Week 3: real time

Goal: no human runs `agent.investigate` by hand anymore.

1. `webhook.py`: a FastAPI app with `POST /incident` that accepts the failure event JSON
   and runs `agent.investigate.investigate(event)` in a background task.
2. Post the report to Slack with `requests.post(SLACK_WEBHOOK_URL, json={"text": report})`.
3. Airflow: wrap the pipeline steps in a DAG (Astro CLI: `astro dev init`) and add an
   `on_failure_callback` that POSTs the event to `http://host.docker.internal:8000/incident`.
