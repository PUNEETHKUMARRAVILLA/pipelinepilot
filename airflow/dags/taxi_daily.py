"""
## taxi_daily

The PipelinePilot "patient" pipeline, run by Airflow: the same four steps as
`pipeline/run.py`, one task each. When any task fails, `on_failure_callback`
records the failure and hands it to the PipelinePilot web server, which runs the
agent and posts the root cause to Slack.
"""
import re
from contextlib import contextmanager
import duckdb
from airflow.sdk import dag, task
from pendulum import datetime

from pipeline import run as pipeline_run
from pipeline.config import DB_PATH


def _run_id(context) -> str:
    # Airflow ids look like "manual__2026-09-26T10:00:00+00:00"; the agent's tools accept only [A-Za-z0-9_]
    return re.sub(r"[^A-Za-z0-9_]", "_", context["dag_run"].run_id)


def _started(context):
    # Airflow keeps times in UTC; pipeline_runs uses this Mac's local time (TZ in airflow/.env)
    return context["dag_run"].start_date.astimezone().replace(tzinfo=None)


@contextmanager
def _step(context):
    """Warehouse connection + the run's log file (logs/run_<id>.log, which the agent reads)."""
    log = pipeline_run.setup_logger(_run_id(context))
    con = duckdb.connect(str(DB_PATH))
    try:
        pipeline_run.init_db(con)
        yield con, log
    finally:
        con.close()


def report_failure(context) -> None:
    """on_failure_callback: record the failed run and alert PipelinePilot."""
    run_id = _run_id(context)
    exc = context.get("exception")
    row_count = context["ti"].xcom_pull(task_ids="staging")  # None if staging never finished
    event = pipeline_run.record_failure(
        run_id=run_id,
        started=_started(context),
        step=context["ti"].task_id,
        error=f"{type(exc).__name__}: {exc}",
        row_count=row_count,
        log=pipeline_run.setup_logger(run_id),
    )
    pipeline_run.notify_agent(event)


@dag(
    schedule="@daily",
    start_date=datetime(2026, 9, 1),
    catchup=False,
    doc_md=__doc__,
    # retries=0: a broken file stays broken, so retrying only delays the alert
    default_args={"owner": "pipelinepilot", "retries": 0, "on_failure_callback": report_failure},
    tags=["pipelinepilot"],
)
def taxi_daily():
    @task
    def extract(**context):
        with _step(context) as (con, log):
            pipeline_run.step_extract(con, log)

    @task
    def staging(**context) -> int:
        with _step(context) as (con, log):
            return pipeline_run.step_staging(con, log)

    @task
    def quality_checks(row_count: int, **context) -> int:
        with _step(context) as (con, log):
            pipeline_run.step_quality_checks(con, log, row_count)
        return row_count

    @task
    def mart(row_count: int, **context):
        with _step(context) as (con, log):
            pipeline_run.step_mart(con, log)
        pipeline_run.record_success(_run_id(context), _started(context), row_count, log)

    rows = staging()
    extract() >> rows
    mart(quality_checks(rows))


taxi_daily()
