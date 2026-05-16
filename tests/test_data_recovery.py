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


# ---------------------------------------------------------------------------
# New test cases (P1 / P2)
# ---------------------------------------------------------------------------

def test_restore_table_verifies_data(cur):
    """RESTORE TABLE must preserve the correct row count."""
    # Record the current row count before restore.
    cur.execute(f'SELECT COUNT(*) FROM {T}')
    original_count = cur.fetchone()[0]

    # Get the latest version timestamp from DESC HISTORY.
    cur.execute(f'DESC HISTORY {T}')
    rows = cur.fetchall()
    col_names = [d[0].lower() for d in cur.description]
    time_idx = col_names.index('time')
    version_idx = col_names.index('version')
    latest = sorted(rows, key=lambda r: r[version_idx])[-1]
    ts = latest[time_idx]

    # Restore to the latest version (idempotent) and verify row count.
    run_sql(cur, f"RESTORE TABLE {T} TO TIMESTAMP AS OF '{ts}'")
    cur.execute(f'SELECT COUNT(*) FROM {T}')
    restored_count = cur.fetchone()[0]
    assert restored_count == original_count, (
        f"Row count after RESTORE ({restored_count}) != original ({original_count})"
    )


def test_time_travel_relative_interval(cur):
    """SELECT ... TIMESTAMP AS OF CURRENT_TIMESTAMP() - INTERVAL N syntax must be accepted.

    Uses CURRENT_TIMESTAMP() (zero offset) to guarantee a valid version exists.
    The INTERVAL arithmetic syntax is what is being validated here.
    """
    # CURRENT_TIMESTAMP() - INTERVAL 0 SECOND resolves to now, which always has a version.
    cur.execute(
        f"SELECT COUNT(*) FROM {T} TIMESTAMP AS OF CURRENT_TIMESTAMP() - INTERVAL 0 SECOND"
    )
    rows = cur.fetchall()
    assert rows[0][0] >= 0, "COUNT(*) must be non-negative"


def test_show_tables_history_like(cur):
    """SHOW TABLES HISTORY IN schema LIKE pattern must work."""
    cur.execute(f"SHOW TABLES HISTORY IN {SCHEMA} LIKE 'recovery%'")
    rows = cur.fetchall()
    assert len(rows) >= 1, "Expected at least one row matching 'recovery%'"
    col_names = [d[0].lower() for d in cur.description]
    assert 'table_name' in col_names, f"Missing 'table_name' column, got: {col_names}"


def test_undrop_table_verifies_data(cur):
    """UNDROP TABLE must restore all rows (data integrity check)."""
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SCHEMA}.undrop_verify_p3 (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {SCHEMA}.undrop_verify_p3 VALUES (1,'a'),(2,'b'),(3,'c')")
    run_sql(cur, f'DROP TABLE {SCHEMA}.undrop_verify_p3')
    run_sql(cur, f'UNDROP TABLE {SCHEMA}.undrop_verify_p3')
    cur.execute(f'SELECT COUNT(*) FROM {SCHEMA}.undrop_verify_p3')
    count = cur.fetchone()[0]
    assert count == 3, f"UNDROP should restore all 3 rows, got {count}"
    run_sql(cur, f'DROP TABLE IF EXISTS {SCHEMA}.undrop_verify_p3')
