"""
Validation tests for clickzetta-access-control skill.

Covers:
- SHOW NETWORK POLICY (singular, not POLICIES)
- CREATE NETWORK POLICY syntax
- GRANT / REVOKE syntax
- SHOW GRANTS
- CREATE ROLE / DROP ROLE
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
ROLE = 'skill_test_readonly_role'
POLICY = 'skill_test_net_policy'


@pytest.fixture(scope='module', autouse=True)
def cleanup(cur):
    yield
    for sql in [
        f'DROP ROLE IF EXISTS {ROLE}',
        f'DROP NETWORK POLICY IF EXISTS {POLICY}',
    ]:
        try:
            cur.execute(sql)
        except Exception:
            pass


def test_show_network_policy_singular(cur):
    """SHOW NETWORK POLICY (singular) must work."""
    run_sql(cur, 'SHOW NETWORK POLICY')


def test_show_network_policies_plural_fails(cur):
    """SHOW NETWORK POLICIES (plural) must fail."""
    run_sql(cur, 'SHOW NETWORK POLICIES', expect_error=True)


def test_create_network_policy_allowed_list(cur):
    """CREATE NETWORK POLICY with ALLOWED_IP_LIST must work."""
    run_sql(cur, f"""
        CREATE NETWORK POLICY IF NOT EXISTS {POLICY}
          ALLOWED_IP_LIST = ('10.0.0.0/8')
          COMMENT '测试网络策略'
    """)


def test_create_role(cur):
    """CREATE ROLE must work."""
    run_sql(cur, f"CREATE ROLE IF NOT EXISTS {ROLE} COMMENT '只读测试角色'")


def test_show_roles(cur):
    """SHOW ROLES must work."""
    run_sql(cur, 'SHOW ROLES')


def test_show_grants(cur):
    """SHOW GRANTS must work."""
    run_sql(cur, 'SHOW GRANTS')


def test_grant_select_on_table(cur):
    """GRANT SELECT on a table to a role must work."""
    # Need a table to grant on
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SCHEMA}.grant_test (id INT)')
    run_sql(cur, f'GRANT SELECT ON TABLE {SCHEMA}.grant_test TO ROLE {ROLE}')
    run_sql(cur, f'DROP TABLE IF EXISTS {SCHEMA}.grant_test')


def test_revoke_select_on_table(cur):
    """REVOKE SELECT must work."""
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SCHEMA}.revoke_test (id INT)')
    run_sql(cur, f'GRANT SELECT ON TABLE {SCHEMA}.revoke_test TO ROLE {ROLE}')
    run_sql(cur, f'REVOKE SELECT ON TABLE {SCHEMA}.revoke_test FROM ROLE {ROLE}')
    run_sql(cur, f'DROP TABLE IF EXISTS {SCHEMA}.revoke_test')


def test_drop_role(cur):
    """DROP ROLE IF EXISTS must work."""
    run_sql(cur, f'DROP ROLE IF EXISTS {ROLE}')


def test_drop_network_policy(cur):
    """DROP NETWORK POLICY IF EXISTS must work."""
    run_sql(cur, f'DROP NETWORK POLICY IF EXISTS {POLICY}')
