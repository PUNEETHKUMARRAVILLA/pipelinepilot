"""Run:  pytest -q"""
import pytest

from agent.tools import get_pipeline_code, validate_sql


@pytest.mark.parametrize("q", [
    "SELECT count(*) FROM staging.trips",
    "with t as (select 1) select * from t;",
])
def test_allows_read_only(q):
    assert validate_sql(q)


@pytest.mark.parametrize("q", [
    "DROP TABLE staging.trips",
    "DELETE FROM raw.trips",
    "SELECT 1; DROP TABLE raw.trips",
    "CREATE TABLE x AS SELECT 1",
    "SELECT * FROM raw.trips WHERE 1=1 AND (SELECT 1) = 1; UPDATE raw.trips SET trip_id = 0",
    "ATTACH 'other.db'",
])
def test_blocks_writes(q):
    with pytest.raises(ValueError):
        validate_sql(q)


def test_pipeline_code_shows_staging_sql():
    assert "fare_amount" in get_pipeline_code("staging")


def test_pipeline_code_rejects_unknown_step():
    assert get_pipeline_code("../../.env").startswith("Unknown step")
