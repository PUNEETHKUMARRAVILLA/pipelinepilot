"""Shared paths and settings for the pipeline and the agent."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_FILE = RAW_DIR / "trips_latest.csv"
DB_PATH = DATA_DIR / "warehouse.duckdb"
LOG_DIR = ROOT / "logs"
LAST_FAILURE = LOG_DIR / "last_failure.json"
# Written by break_it.py so evals can grade the agent later.
# The agent's tools never read this file.
INJECTED = LOG_DIR / "injected_failure.json"

PIPELINE_NAME = "taxi_daily"
# Where a failed run reports itself (app/webhook.py). Airflow runs inside Docker, so its
# airflow/.env points this at host.docker.internal (= "this Mac, seen from a container").
AGENT_WEBHOOK_URL = os.getenv("AGENT_WEBHOOK_URL", "http://localhost:8000/incident")

for d in (DATA_DIR, RAW_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)
