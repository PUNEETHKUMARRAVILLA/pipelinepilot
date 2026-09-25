"""Run:  pytest -q"""
import pytest

from agent.tools import validate_sql


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
