"""Read-only tools the agent can call. Each is a plain Python function that returns text.

Guardrails live HERE, in code, not only in the prompt:
- the warehouse is opened read_only=True
- run_sql only accepts a single SELECT / WITH statement
- results are capped at MAX_ROWS rows
"""
import csv
import inspect
import json
import re
from datetime import datetime

import duckdb

from pipeline import run as pipeline_run
from pipeline.config import DB_PATH, LOG_DIR, RAW_FILE

MAX_ROWS = 100
_BLOCKED = re.compile(
    r"\b(insert|update|delete|drop|create|alter|attach|detach|copy|export|import|install|load|pragma|set|call|checkpoint)\b",
    re.IGNORECASE,
)
_TABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def _connect():
    return duckdb.connect(str(DB_PATH), read_only=True)


def _as_table(cols, rows) -> str:
    lines = [" | ".join(cols)]
    lines += [" | ".join("NULL" if v is None else str(v) for v in r) for r in rows]
    return "\n".join(lines)


def _check_table(name: str) -> str:
    if not _TABLE_NAME.match(name):
        raise ValueError(f"Invalid table name: {name!r}")
    return name


def validate_sql(query: str) -> str:
    """Raise ValueError unless the query is one read-only statement."""
    q = query.strip().rstrip(";").strip()
    if ";" in q:
        raise ValueError("Only one statement is allowed.")
    if not re.match(r"^(select|with)\b", q, re.IGNORECASE):
        raise ValueError("Only SELECT or WITH queries are allowed.")
    if _BLOCKED.search(q):
        raise ValueError("Query contains a keyword that is not allowed in read-only mode.")
    return q


# ---------------- the tools ----------------

def get_run_logs(run_id: str, max_lines: int = 60) -> str:
    if not re.match(r"^[A-Za-z0-9_]+$", run_id):
        return "Invalid run_id."
    path = LOG_DIR / f"run_{run_id}.log"
    if not path.exists():
        return f"No log file for run {run_id}."
    lines = path.read_text().splitlines()
    return "\n".join(lines[-max_lines:])


def get_recent_runs(limit: int = 5) -> str:
    with _connect() as con:
        cur = con.execute(
            "SELECT run_id, status, failed_step, error, row_count, finished_at "
            f"FROM pipeline_runs ORDER BY finished_at DESC LIMIT {min(int(limit), 20)}")
        return _as_table([d[0] for d in cur.description], cur.fetchall())


def list_tables() -> str:
    with _connect() as con:
        cur = con.execute(
            "SELECT table_schema, table_name FROM information_schema.tables ORDER BY 1, 2")
        return _as_table(["schema", "table"], cur.fetchall())


def get_table_schema(table: str) -> str:
    table = _check_table(table)
    with _connect() as con:
        cur = con.execute(f"DESCRIBE {table}")
        rows = [(r[0], r[1]) for r in cur.fetchall()]
        return _as_table(["column", "type"], rows)


def check_source_file() -> str:
    """Header, row count and newest timestamp of the raw source file (outside the warehouse)."""
    if not RAW_FILE.exists():
        return f"Source file {RAW_FILE.name} does not exist."
    with open(RAW_FILE, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        sample = []
        count = 0
        for row in reader:
            count += 1
            if len(sample) < 3:
                sample.append(row)
    modified = datetime.fromtimestamp(RAW_FILE.stat().st_mtime).isoformat(sep=" ", timespec="seconds")
    return json.dumps({"file": RAW_FILE.name, "modified": modified, "rows": count,
                       "columns": header, "first_rows": sample}, indent=2)


def profile_table(table: str) -> str:
    table = _check_table(table)
    with _connect() as con:
        cols = [r[0] for r in con.execute(f"DESCRIBE {table}").fetchall()]
        total = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        out = {"table": table, "rows": total, "null_pct": {}}
        for c in cols:
            nulls = con.execute(f'SELECT count(*) FILTER (WHERE "{c}" IS NULL) FROM {table}').fetchone()[0]
            out["null_pct"][c] = round(100 * nulls / total, 1) if total else None
        if "trip_id" in cols:
            out["duplicate_trip_ids"] = con.execute(
                f"SELECT count(*) - count(DISTINCT trip_id) FROM {table}").fetchone()[0]
        if "pickup_ts" in cols:
            out["min_pickup_ts"], out["max_pickup_ts"] = [
                str(v) for v in con.execute(f"SELECT min(pickup_ts), max(pickup_ts) FROM {table}").fetchone()]
        return json.dumps(out, indent=2)


def run_sql(query: str) -> str:
    q = validate_sql(query)
    with _connect() as con:
        cur = con.execute(f"SELECT * FROM ({q}) AS _q LIMIT {MAX_ROWS}")
        return _as_table([d[0] for d in cur.description], cur.fetchall())


PIPELINE_STEPS = {
    "extract": pipeline_run.step_extract,
    "staging": pipeline_run.step_staging,
    "quality_checks": pipeline_run.step_quality_checks,
    "mart": pipeline_run.step_mart,
}


def get_pipeline_code(step: str) -> str:
    """Source code of one pipeline step, so the agent can see the real SQL it runs."""
    if step not in PIPELINE_STEPS:
        return f"Unknown step '{step}'. Choose from: {', '.join(PIPELINE_STEPS)}"
    return inspect.getsource(PIPELINE_STEPS[step])


# ---------------- what the model sees ----------------

TOOLS = {
    "get_run_logs": get_run_logs,
    "get_recent_runs": get_recent_runs,
    "list_tables": list_tables,
    "get_table_schema": get_table_schema,
    "check_source_file": check_source_file,
    "profile_table": profile_table,
    "run_sql": run_sql,
    "get_pipeline_code": get_pipeline_code,
}

TOOL_SCHEMAS = [
    {"name": "get_run_logs",
     "description": "Return the last lines of the log file for a pipeline run. Start here.",
     "input_schema": {"type": "object", "properties": {
         "run_id": {"type": "string"}, "max_lines": {"type": "integer", "default": 60}},
         "required": ["run_id"]}},
    {"name": "get_recent_runs",
     "description": "Recent pipeline runs with status, failed step, error and row_count. Use to compare against normal runs.",
     "input_schema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 5}}}},
    {"name": "list_tables",
     "description": "List all schemas and tables in the DuckDB warehouse.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_table_schema",
     "description": "Column names and types of a warehouse table, e.g. raw.trips or staging.trips.",
     "input_schema": {"type": "object", "properties": {"table": {"type": "string"}}, "required": ["table"]}},
    {"name": "check_source_file",
     "description": "Inspect the raw CSV source file directly: header columns, row count, first rows, modified time.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "profile_table",
     "description": "Row count, null % per column, duplicate trip_ids and pickup time range for a table.",
     "input_schema": {"type": "object", "properties": {"table": {"type": "string"}}, "required": ["table"]}},
    {"name": "run_sql",
     "description": f"Run ONE read-only SELECT/WITH query on DuckDB. Max {MAX_ROWS} rows returned.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_pipeline_code",
     "description": "Source code (including the SQL) of one pipeline step, e.g. staging. "
                    "Use it to see which columns the step expects instead of guessing.",
     "input_schema": {"type": "object", "properties": {
         "step": {"type": "string", "enum": list(PIPELINE_STEPS)}}, "required": ["step"]}},
]
