"""
Validation tests for clickzetta-data-lifecycle skill.

Covers:
- DESC HISTORY (returns version, time, total_rows, total_bytes, user, operation)
- RESTORE TABLE TO TIMESTAMP
- UNDROP TABLE
- Time Travel SELECT TIMESTAMP AS OF
- ALTER TABLE SET PROPERTIES (data_lifecycle)
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T = f'{SCHEMA}.lifecycle_test'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {T} (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {T} VALUES (1, 'v1')")
    run_sql(cur, f"INSERT INTO {T} VALUES (2, 'v2')")
    yield
    try:
        cur.execute(f'DROP TABLE IF EXISTS {T}')
    except Exception:
        pass


def test_desc_history_columns(cur):
    """DESC HISTORY must return version, time, total_rows, total_bytes columns."""
    cur.execute(f'DESC HISTORY {T}')
    rows = cur.fetchall()
    assert len(rows) > 0, "DESC HISTORY should return at least one row"
    # Check column names from description
    col_names = [d[0].lower() for d in cur.description]
    assert 'version' in col_names, f"Missing 'version' column, got: {col_names}"
    assert 'total_rows' in col_names, f"Missing 'total_rows' column, got: {col_names}"
    assert 'total_bytes' in col_names, f"Missing 'total_bytes' column, got: {col_names}"
    assert 'operation' in col_names, f"Missing 'operation' column, got: {col_names}"


def test_time_travel_timestamp_as_of(cur):
    """SELECT ... TIMESTAMP AS OF must work."""
    cur.execute(f'DESC HISTORY {T}')
    rows = cur.fetchall()
    col_names = [d[0].lower() for d in cur.description]
    time_idx = col_names.index('time')
    # Use the earliest version's timestamp
    earliest_time = sorted(rows, key=lambda r: r[col_names.index('version')])[0][time_idx]
    run_sql(cur, f"SELECT * FROM {T} TIMESTAMP AS OF '{earliest_time}'")


def test_alter_table_data_lifecycle(cur):
    """ALTER TABLE SET PROPERTIES data_lifecycle must work."""
    run_sql(cur, f"ALTER TABLE {T} SET PROPERTIES ('data_lifecycle' = '30')")


def test_undrop_table(cur):
    """UNDROP TABLE must work after DROP."""
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'UNDROP TABLE {T}')


def test_restore_table(cur):
    """RESTORE TABLE TO TIMESTAMP must work."""
    cur.execute(f'DESC HISTORY {T}')
    rows = cur.fetchall()
    col_names = [d[0].lower() for d in cur.description]
    time_idx = col_names.index('time')
    version_idx = col_names.index('version')
    # Restore to earliest version
    earliest = sorted(rows, key=lambda r: r[version_idx])[0]
    ts = earliest[time_idx]
    run_sql(cur, f"RESTORE TABLE {T} TO TIMESTAMP AS OF '{ts}'")
