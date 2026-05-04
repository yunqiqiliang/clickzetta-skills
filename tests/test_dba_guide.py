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
