"""
Validation tests for clickzetta-dba-guide skill.

Covers:
- CREATE USER / DROP USER / SHOW USERS
- CREATE ROLE / DROP ROLE / SHOW ROLES
- GRANT ROLE TO USER / REVOKE ROLE FROM USER
- GRANT SELECT ON TABLE / REVOKE
- SHOW GRANTS TO USER / ROLE
- CREATE NETWORK POLICY (COMMENT without =)
- SHOW NETWORK POLICY (singular)
- DROP NETWORK POLICY
- OPTIMIZE table
- ANALYZE TABLE
- SHOW JOBS
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T = f'{SCHEMA}.dba_test'
TEST_ROLE = 'skill_test_role_tmp'
TEST_POLICY = 'skill_test_policy_tmp'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'CREATE TABLE {T} (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {T} VALUES (1, 'a'), (2, 'b'), (3, 'c')")
    yield
    try:
        cur.execute(f'DROP TABLE IF EXISTS {T}')
    except Exception:
        pass


@pytest.fixture(scope='module', autouse=True)
def cleanup_role(cur, setup):
    yield
    try:
        cur.execute(f'DROP ROLE IF EXISTS {TEST_ROLE}')
    except Exception:
        pass


@pytest.fixture(scope='module', autouse=True)
def cleanup_policy(cur, setup):
    yield
    try:
        cur.execute(f'DROP NETWORK POLICY IF EXISTS {TEST_POLICY}')
    except Exception:
        pass


def test_show_users(cur):
    """SHOW USERS must work."""
    run_sql(cur, 'SHOW USERS')


def test_create_role(cur):
    """CREATE ROLE must work."""
    run_sql(cur, f'DROP ROLE IF EXISTS {TEST_ROLE}')
    run_sql(cur, f'CREATE ROLE {TEST_ROLE}')


def test_show_roles(cur):
    """SHOW ROLES must work."""
    run_sql(cur, 'SHOW ROLES')


def test_grant_select_on_table(cur):
    """GRANT SELECT ON TABLE must work."""
    import os
    user = os.environ.get('CLICKZETTA_USERNAME', 'admin')
    run_sql(cur, f'GRANT SELECT ON TABLE {T} TO USER {user}')


def test_show_grants_to_user(cur):
    """SHOW GRANTS TO USER must work."""
    import os
    user = os.environ.get('CLICKZETTA_USERNAME', 'admin')
    run_sql(cur, f'SHOW GRANTS TO USER {user}')


def test_show_grants_to_role(cur):
    """SHOW GRANTS TO ROLE must work."""
    run_sql(cur, f'SHOW GRANTS TO ROLE {TEST_ROLE}')


def test_revoke_select_on_table(cur):
    """REVOKE SELECT ON TABLE must work."""
    import os
    user = os.environ.get('CLICKZETTA_USERNAME', 'admin')
    run_sql(cur, f'REVOKE SELECT ON TABLE {T} FROM USER {user}')


def test_drop_role(cur):
    """DROP ROLE IF EXISTS must work."""
    run_sql(cur, f'DROP ROLE IF EXISTS {TEST_ROLE}')


def test_create_network_policy_comment_no_equals(cur):
    """CREATE NETWORK POLICY with COMMENT (no =) must work."""
    run_sql(cur, f'DROP NETWORK POLICY IF EXISTS {TEST_POLICY}')
    run_sql(cur, f"""
        CREATE NETWORK POLICY {TEST_POLICY}
          ALLOWED_IP_LIST = ('10.0.0.0/8')
          COMMENT '测试策略，可删除'
    """)


def test_create_network_policy_comment_with_equals_fails(cur):
    """CREATE NETWORK POLICY with COMMENT = '...' must fail."""
    err = run_sql(cur, f"""
        CREATE NETWORK POLICY skill_test_policy_wrong
          ALLOWED_IP_LIST = ('10.0.0.0/8')
          COMMENT = '错误语法'
    """, expect_error=True)
    assert err, "Expected syntax error for COMMENT = '...' in NETWORK POLICY"
    try:
        cur.execute('DROP NETWORK POLICY IF EXISTS skill_test_policy_wrong')
    except Exception:
        pass


def test_show_network_policy_singular(cur):
    """SHOW NETWORK POLICY (singular) must work."""
    run_sql(cur, 'SHOW NETWORK POLICY')


def test_drop_network_policy(cur):
    """DROP NETWORK POLICY IF EXISTS must work."""
    run_sql(cur, f'DROP NETWORK POLICY IF EXISTS {TEST_POLICY}')


def test_optimize_table(cur):
    """OPTIMIZE table must work."""
    run_sql(cur, f'OPTIMIZE {T}')


def test_analyze_table(cur):
    """ANALYZE TABLE must work."""
    run_sql(cur, f'ANALYZE TABLE {T}')


def test_show_jobs(cur):
    """SHOW JOBS must work."""
    run_sql(cur, 'SHOW JOBS LIMIT 5')


# ---------------------------------------------------------------------------
# P1: UNDROP TABLE
# ---------------------------------------------------------------------------

def test_undrop_table(cur):
    """UNDROP TABLE should restore a dropped table and preserve its data."""
    T = f'{SCHEMA}.undrop_test'
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'CREATE TABLE {T} (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {T} VALUES (1, 'a')")
    run_sql(cur, f'DROP TABLE {T}')
    run_sql(cur, f'UNDROP TABLE {T}')
    cur.execute(f'SELECT COUNT(*) FROM {T}')
    count = cur.fetchone()[0]
    assert count == 1, f"Expected 1 row after UNDROP, got {count}"
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')


# ---------------------------------------------------------------------------
# P1: RESTORE TABLE
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def restore_table(cur):
    """Create and populate restore_test table; yield table name; drop on teardown."""
    import time
    import datetime
    T = f'{SCHEMA}.restore_test'
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'CREATE TABLE {T} (id INT)')
    run_sql(cur, f'INSERT INTO {T} VALUES (1),(2),(3)')
    time.sleep(3)
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    time.sleep(3)
    run_sql(cur, f'DELETE FROM {T} WHERE id = 3')
    yield T, ts
    try:
        cur.execute(f'DROP TABLE IF EXISTS {T}')
    except Exception:
        pass


def test_restore_table_correct_syntax(cur, restore_table):
    """RESTORE TABLE with CAST() syntax should restore data to the given timestamp."""
    T, ts = restore_table
    run_sql(cur, f"RESTORE TABLE {T} TO TIMESTAMP AS OF CAST('{ts}' AS TIMESTAMP)")
    cur.execute(f'SELECT COUNT(*) FROM {T}')
    count = cur.fetchone()[0]
    assert count == 3, f"Expected 3 rows after RESTORE, got {count}"


def test_restore_table_wrong_syntax_fails(cur, restore_table):
    """RESTORE TABLE with a bare string literal (no CAST) must fail."""
    T, _ = restore_table
    err = run_sql(
        cur,
        f"RESTORE TABLE {T} TO TIMESTAMP AS OF '2024-01-01 00:00:00'",
        expect_error=True,
    )
    assert err, "Expected syntax error for bare string in RESTORE TABLE"


# ---------------------------------------------------------------------------
# P2: OPTIMIZE variants
# ---------------------------------------------------------------------------

def test_optimize_table_nosuffix(cur):
    """OPTIMIZE table (no extra clause) must work."""
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {T} (id INT, val STRING)')
    run_sql(cur, f'OPTIMIZE {T}')


def test_optimize_with_partition_filter(cur):
    """OPTIMIZE with WHERE partition filter currently fails (partition column not resolvable).

    Verified 2026-05-16: CZLH-42000 - partition column cannot be resolved.
    Recorded as expected failure so the test suite documents the limitation.
    """
    PT = f'{SCHEMA}.opt_part'
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    run_sql(cur, f'DROP TABLE IF EXISTS {PT}')
    run_sql(cur, f'CREATE TABLE {PT} (id INT, dt DATE) PARTITIONED BY (days(dt))')
    run_sql(cur, f"INSERT INTO {PT} VALUES (1, DATE '2024-01-01')")
    err = run_sql(
        cur,
        f"OPTIMIZE {PT} WHERE dt = DATE '2024-01-01'",
        expect_error=True,
    )
    assert err, "Expected error: partition column cannot be resolved in OPTIMIZE WHERE"
    run_sql(cur, f'DROP TABLE IF EXISTS {PT}')


# ---------------------------------------------------------------------------
# P2: ANALYZE TABLE variants
# ---------------------------------------------------------------------------

def test_analyze_table_noscan(cur):
    """ANALYZE TABLE ... COMPUTE STATISTICS NOSCAN must work."""
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {T} (id INT, val STRING)')
    run_sql(cur, f'ANALYZE TABLE {T} COMPUTE STATISTICS NOSCAN')


def test_analyze_table_for_columns(cur):
    """ANALYZE TABLE ... FOR COLUMNS is not supported (syntax error).

    Verified 2026-05-16: CZLH-42000 - Syntax error at or near 'COLUMNS'.
    Recorded as expected failure to document the unsupported syntax.
    """
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {T} (id INT, val STRING)')
    err = run_sql(
        cur,
        f'ANALYZE TABLE {T} FOR COLUMNS id, val',
        expect_error=True,
    )
    assert err, "Expected syntax error for ANALYZE TABLE ... FOR COLUMNS"


# ---------------------------------------------------------------------------
# P2: SHOW JOBS IN VCLUSTER
# ---------------------------------------------------------------------------

def test_show_jobs_in_vcluster(cur):
    """SHOW JOBS IN VCLUSTER DEFAULT LIMIT 5 must work."""
    run_sql(cur, 'SHOW JOBS IN VCLUSTER DEFAULT LIMIT 5')


# ---------------------------------------------------------------------------
# P3: DESC HISTORY
# ---------------------------------------------------------------------------

def test_desc_history(cur):
    """DESC HISTORY must work on an existing table."""
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {T} (id INT, val STRING)')
    run_sql(cur, f'DESC HISTORY {T}')


# ---------------------------------------------------------------------------
# P3: TRUNCATE TABLE
# ---------------------------------------------------------------------------

def test_truncate_table(cur):
    """TRUNCATE TABLE must empty the table."""
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {T} (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {T} VALUES (99, 'tmp')")
    run_sql(cur, f'TRUNCATE TABLE {T}')
    cur.execute(f'SELECT COUNT(*) FROM {T}')
    count = cur.fetchone()[0]
    assert count == 0, f"Expected 0 rows after TRUNCATE, got {count}"
