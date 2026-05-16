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


# ---------------------------------------------------------------------------
# New test cases (P1 / P2)
# ---------------------------------------------------------------------------

def test_alter_data_retention_days(cur):
    """ALTER TABLE SET PROPERTIES data_retention_days must work and be reflected in SHOW CREATE TABLE."""
    run_sql(cur, f"ALTER TABLE {T} SET PROPERTIES ('data_retention_days'='7')")
    cur.execute(f'SHOW CREATE TABLE {T}')
    rows = cur.fetchall()
    ddl = str(rows)
    assert 'data_retention_days' in ddl, (
        f"Expected 'data_retention_days' in SHOW CREATE TABLE output, got: {ddl[:400]}"
    )


def test_alter_data_lifecycle_disable(cur):
    """ALTER TABLE SET PROPERTIES data_lifecycle='-1' (disable) must work."""
    run_sql(cur, f"ALTER TABLE {T} SET PROPERTIES ('data_lifecycle'='-1')")


def test_show_tables_history(cur):
    """SHOW TABLES HISTORY IN schema must work."""
    run_sql(cur, f'SHOW TABLES HISTORY IN {SCHEMA}')


def test_show_tables_history_like(cur):
    """SHOW TABLES HISTORY IN schema LIKE pattern must work."""
    cur.execute(f"SHOW TABLES HISTORY IN {SCHEMA} LIKE 'lifecycle%'")
    rows = cur.fetchall()
    assert len(rows) >= 1, "Expected at least one row matching 'lifecycle%'"
    col_names = [d[0].lower() for d in cur.description]
    assert 'table_name' in col_names, f"Missing 'table_name' column, got: {col_names}"


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


def test_alter_data_lifecycle_verify_with_show_create(cur):
    """SET PROPERTIES data_lifecycle then SHOW CREATE TABLE must reflect the value."""
    run_sql(cur, f"ALTER TABLE {T} SET PROPERTIES ('data_lifecycle'='30')")
    cur.execute(f'SHOW CREATE TABLE {T}')
    rows = cur.fetchall()
    ddl = str(rows)
    assert 'data_lifecycle' in ddl, (
        f"Expected 'data_lifecycle' in SHOW CREATE TABLE output, got: {ddl[:400]}"
    )
    assert '30' in ddl, (
        f"Expected value '30' in SHOW CREATE TABLE output, got: {ddl[:400]}"
    )
