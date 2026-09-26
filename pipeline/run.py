"""The "patient": a small ELT pipeline  raw CSV -> raw -> staging -> mart, with data-quality checks.

Run:  python -m pipeline.run
On failure it records the run in pipeline_runs, writes logs/run_<id>.log and
logs/last_failure.json (the event the agent will investigate), and exits with code 1.
In week 3 Airflow will call these same steps and fire a webhook instead.
"""
import json
import logging
import sys
import uuid
from datetime import datetime

import duckdb

from pipeline.config import DB_PATH, LAST_FAILURE, LOG_DIR, PIPELINE_NAME, RAW_FILE


class DataQualityError(Exception):
    pass


def setup_logger(run_id: str) -> logging.Logger:
    log = logging.getLogger(run_id)
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(LOG_DIR / f"run_{run_id}.log")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)
    return log


def init_db(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    con.execute("CREATE SCHEMA IF NOT EXISTS mart")
    con.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id VARCHAR, pipeline VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP,
            status VARCHAR, failed_step VARCHAR, error VARCHAR, row_count BIGINT)
    """)


def step_extract(con, log):
    log.info("extract: loading %s into raw.trips", RAW_FILE.name)
    con.execute(f"CREATE OR REPLACE TABLE raw.trips AS SELECT * FROM read_csv_auto('{RAW_FILE.as_posix()}', all_varchar=true)")
    n = con.execute("SELECT count(*) FROM raw.trips").fetchone()[0]
    log.info("extract: %s rows loaded", n)


def step_staging(con, log):
    log.info("staging: casting types into staging.trips")
    con.execute("""
        CREATE OR REPLACE TABLE staging.trips AS
        SELECT
            CAST(trip_id AS BIGINT)          AS trip_id,
            CAST(pickup_ts AS TIMESTAMP)     AS pickup_ts,
            CAST(dropoff_ts AS TIMESTAMP)    AS dropoff_ts,
            pickup_zone,
            CAST(passenger_count AS INTEGER) AS passenger_count,
            CAST(trip_distance AS DOUBLE)    AS trip_distance,
            CAST(fare_amount AS DOUBLE)      AS fare_amount,
            CAST(tip_amount AS DOUBLE)       AS tip_amount,
            CAST(total_amount AS DOUBLE)     AS total_amount,
            payment_type
        FROM raw.trips
    """)
    n = con.execute("SELECT count(*) FROM staging.trips").fetchone()[0]
    log.info("staging: %s rows", n)
    return n


def step_quality_checks(con, log, row_count):
    log.info("quality: running checks on staging.trips")

    null_pct = con.execute(
        "SELECT 100.0 * count(*) FILTER (WHERE pickup_zone IS NULL OR pickup_zone = '') / count(*) FROM staging.trips"
    ).fetchone()[0]
    if null_pct > 5:
        raise DataQualityError(f"check_not_null(pickup_zone) failed: {null_pct:.1f}% null (threshold 5%)")

    dupes = con.execute("SELECT count(*) - count(DISTINCT trip_id) FROM staging.trips").fetchone()[0]
    if dupes > 0:
        raise DataQualityError(f"check_unique(trip_id) failed: {dupes} duplicate trip_id values")

    fresh = con.execute(
        "SELECT max(pickup_ts) >= now()::TIMESTAMP - INTERVAL 1 DAY FROM staging.trips"
    ).fetchone()[0]
    if not fresh:
        raise DataQualityError("check_freshness(pickup_ts) failed: newest record is older than 1 day")

    prev = con.execute(
        "SELECT row_count FROM pipeline_runs WHERE status = 'success' ORDER BY finished_at DESC LIMIT 1"
    ).fetchone()
    if prev and row_count < 0.5 * prev[0]:
        raise DataQualityError(
            f"check_volume failed: {row_count} rows vs {prev[0]} in last successful run (min 50%)")
    log.info("quality: all checks passed")


def step_mart(con, log):
    log.info("mart: building mart.daily_zone_revenue")
    con.execute("""
        CREATE OR REPLACE TABLE mart.daily_zone_revenue AS
        SELECT pickup_ts::DATE AS trip_date, pickup_zone,
               count(*) AS trips, round(sum(total_amount), 2) AS revenue
        FROM staging.trips GROUP BY ALL ORDER BY trip_date, revenue DESC
    """)


def main() -> int:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:4]
    log = setup_logger(run_id)
    started = datetime.now()
    con = duckdb.connect(str(DB_PATH))
    init_db(con)
    step, row_count = "start", None
    try:
        step = "extract"; step_extract(con, log)
        step = "staging"; row_count = step_staging(con, log)
        step = "quality_checks"; step_quality_checks(con, log, row_count)
        step = "mart"; step_mart(con, log)
    except Exception as e:  # noqa: BLE001 - we want every failure recorded
        log.error("step %s FAILED: %s: %s", step, type(e).__name__, e)
        con.execute("INSERT INTO pipeline_runs VALUES (?, ?, ?, ?, 'failed', ?, ?, ?)",
                    [run_id, PIPELINE_NAME, started, datetime.now(), step, f"{type(e).__name__}: {e}", row_count])
        event = {"pipeline": PIPELINE_NAME, "run_id": run_id, "failed_step": step,
                 "error": f"{type(e).__name__}: {e}", "failed_at": datetime.now().isoformat()}
        LAST_FAILURE.write_text(json.dumps(event, indent=2))
        con.close()
        print(f"\nRun {run_id} FAILED at step '{step}'. Event written to {LAST_FAILURE.name}.")
        print("Next: python -m agent.investigate")
        return 1

    con.execute("INSERT INTO pipeline_runs VALUES (?, ?, ?, ?, 'success', NULL, NULL, ?)",
                [run_id, PIPELINE_NAME, started, datetime.now(), row_count])
    con.close()
    LAST_FAILURE.unlink(missing_ok=True)  # healthy again: nothing left to investigate
    log.info("run %s succeeded", run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
