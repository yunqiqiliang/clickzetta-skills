"""
Validation tests for clickzetta-data-recovery skill.

Covers:
- DESC HISTORY columns (version, time, total_rows, total_bytes, operation)
- SHOW TABLES HISTORY
- SHOW TABLES HISTORY WHERE delete_time IS NOT NULL
- Time Travel: SELECT ... TIMESTAMP AS OF
- RESTORE TABLE TO TIMESTAMP AS OF
- UNDROP TABLE
- ALTER TABLE SET PROPERTIES data_retention_days
- data_retention_days vs data_lifecycle distinction
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T = f'{SCHEMA}.recovery_test'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'CREATE TABLE {T} (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {T} VALUES (1, 'v1')")
    run_sql(cur, f"INSERT INTO {T} VALUES (2, 'v2')")
    yield
    try:
        cur.execute(f'DROP TABLE IF EXISTS {T}')
    except Exception:
        pass


def test_desc_history_columns(cur):
    """DESC HISTORY must return version, time, total_rows, total_bytes, operation."""
    cur.execute(f'DESC HISTORY {T}')
    rows = cur.fetchall()
    assert len(rows) > 0
    col_names = [d[0].lower() for d in cur.description]
    for col in ['version', 'time', 'total_rows', 'total_bytes', 'operation']:
        assert col in col_names, f"Missing '{col}' in DESC HISTORY, got: {col_names}"


def test_show_tables_history(cur):
    """SHOW TABLES HISTORY must work."""
    run_sql(cur, f'SHOW TABLES HISTORY IN {SCHEMA}')


def test_show_tables_history_where_deleted(cur):
    """SHOW TABLES HISTORY WHERE delete_time IS NOT NULL must work."""
    run_sql(cur, f'SHOW TABLES HISTORY IN {SCHEMA} WHERE delete_time IS NOT NULL')


def test_time_travel_timestamp_as_of(cur):
    """SELECT ... TIMESTAMP AS OF must work."""
    cur.execute(f'DESC HISTORY {T}')
    rows = cur.fetchall()
    col_names = [d[0].lower() for d in cur.description]
    time_idx = col_names.index('time')
    version_idx = col_names.index('version')
    earliest = sorted(rows, key=lambda r: r[version_idx])[0]
    ts = earliest[time_idx]
    run_sql(cur, f"SELECT * FROM {T} TIMESTAMP AS OF '{ts}'")


def test_alter_data_retention_days(cur):
    """ALTER TABLE SET PROPERTIES data_retention_days must work."""
    run_sql(cur, f"ALTER TABLE {T} SET PROPERTIES ('data_retention_days'='7')")


def test_alter_data_lifecycle(cur):
    """ALTER TABLE SET PROPERTIES data_lifecycle must work."""
    run_sql(cur, f"ALTER TABLE {T} SET PROPERTIES ('data_lifecycle'='30')")


def test_alter_data_lifecycle_disable(cur):
    """ALTER TABLE SET PROPERTIES data_lifecycle='-1' (disable) must work."""
    run_sql(cur, f"ALTER TABLE {T} SET PROPERTIES ('data_lifecycle'='-1')")


def test_restore_table(cur):
    """RESTORE TABLE TO TIMESTAMP AS OF must work."""
    cur.execute(f'DESC HISTORY {T}')
    rows = cur.fetchall()
    col_names = [d[0].lower() for d in cur.description]
    time_idx = col_names.index('time')
    version_idx = col_names.index('version')
    earliest = sorted(rows, key=lambda r: r[version_idx])[0]
    ts = earliest[time_idx]
    run_sql(cur, f"RESTORE TABLE {T} TO TIMESTAMP AS OF '{ts}'")


def test_undrop_table(cur):
    """UNDROP TABLE must work after DROP."""
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'UNDROP TABLE {T}')


def test_time_travel_syntax_at_fails(cur):
    """AT syntax (Snowflake-style) must NOT work."""
    err = run_sql(cur, f"SELECT * FROM {T} AT (TIMESTAMP => '2024-01-01')",
                  expect_error=True)
    assert err, "Expected error for AT syntax (ClickZetta uses TIMESTAMP AS OF)"
