"""A small web server that receives pipeline failures and lets the agent investigate them.

Run:  uvicorn app.webhook:app --port 8000
Then a failure event sent to POST http://localhost:8000/incident ends up as a Slack report.
"""
import json

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel, Field

from agent.investigate import investigate
from app.slack import format_report, post_to_slack
from pipeline.config import LOG_DIR

app = FastAPI(title="PipelinePilot")


class FailureEvent(BaseModel):
    """The JSON a failed pipeline run sends. Anything else is rejected with a 422 error."""
    pipeline: str
    run_id: str = Field(pattern=r"^[A-Za-z0-9_]+$")  # also used in a file name, so no "../" tricks
    failed_step: str
    error: str
    failed_at: str


def handle_incident(event: dict) -> None:
    """Runs after the reply is sent: investigate, save the trace, post to Slack."""
    trace = investigate(event)
    (LOG_DIR / f"trace_{event['run_id']}.json").write_text(json.dumps(trace, indent=2, default=str))
    post_to_slack(format_report(trace))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/incident", status_code=202)
def incident(event: FailureEvent, background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(handle_incident, event.model_dump())
    return {"status": "accepted", "run_id": event.run_id}