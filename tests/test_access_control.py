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


def test_alter_network_policy_inactivate_activate(cur):
    """ALTER NETWORK POLICY INACTIVATE / ACTIVATE must work."""
    policy = f'{SCHEMA}.skill_test_inact_policy'
    run_sql(cur, f"CREATE NETWORK POLICY IF NOT EXISTS {policy} ALLOWED_IP_LIST = ('10.0.0.0/8') COMMENT '测试'")
    run_sql(cur, f'ALTER NETWORK POLICY {policy} INACTIVATE')
    run_sql(cur, f'ALTER NETWORK POLICY {policy} ACTIVATE')
    run_sql(cur, f'DROP NETWORK POLICY IF EXISTS {policy}')


# ── P1 新增用例 ──────────────────────────────────────────────────────────────

def test_show_grants_to_user(cur):
    """SHOW GRANTS TO USER <current_user> must work."""
    run_sql(cur, 'SHOW GRANTS TO USER testwang')


def test_show_grants_to_role(cur):
    """Create role, grant SELECT, SHOW GRANTS TO ROLE, then drop role."""
    tmp_role = 'skill_test_tmp_role2'
    run_sql(cur, f'CREATE ROLE IF NOT EXISTS {tmp_role}')
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SCHEMA}.acm_test (id INT)')
    run_sql(cur, f'GRANT SELECT ON TABLE {SCHEMA}.acm_test TO ROLE {tmp_role}')
    cur.execute(f'SHOW GRANTS TO ROLE {tmp_role}')
    rows = cur.fetchall()
    # 至少应包含刚授予的 SELECT 权限（或其隐含的 READ METADATA）
    assert len(rows) >= 1, f'SHOW GRANTS TO ROLE returned no rows for {tmp_role}'
    run_sql(cur, f'DROP TABLE IF EXISTS {SCHEMA}.acm_test')
    run_sql(cur, f'DROP ROLE IF EXISTS {tmp_role}')


def test_grant_use_on_vcluster(cur):
    """GRANT USE ON VCLUSTER DEFAULT to a role must work."""
    vc_role = 'skill_test_vc_role'
    run_sql(cur, f'CREATE ROLE IF NOT EXISTS {vc_role}')
    run_sql(cur, f'GRANT USE ON VCLUSTER DEFAULT TO ROLE {vc_role}')
    run_sql(cur, f'DROP ROLE IF EXISTS {vc_role}')


# ── P2 新增用例 ──────────────────────────────────────────────────────────────

def test_create_network_policy_blocked_list(cur):
    """CREATE NETWORK POLICY with BLOCKED_IP_LIST must work."""
    blocked_policy = 'skill_test_blocked_policy'
    run_sql(cur, f"""
        CREATE NETWORK POLICY {blocked_policy}
          BLOCKED_IP_LIST = ('192.168.1.100')
          COMMENT '测试黑名单策略'
    """)
    run_sql(cur, f'DROP NETWORK POLICY IF EXISTS {blocked_policy}')


def test_alter_network_policy(cur):
    """CREATE then ALTER NETWORK POLICY (SET syntax) must work."""
    alter_policy = 'skill_test_alter_policy'
    run_sql(cur, f"""
        CREATE NETWORK POLICY IF NOT EXISTS {alter_policy}
          ALLOWED_IP_LIST = ('10.0.0.0/8')
    """)
    # ALTER 需要 SET 关键字，不能直接写 ALLOWED_IP_LIST = (...)
    run_sql(cur, f"""
        ALTER NETWORK POLICY {alter_policy}
          SET ALLOWED_IP_LIST = ('10.0.0.0/8', '192.168.0.0/16')
    """)
    run_sql(cur, f'DROP NETWORK POLICY IF EXISTS {alter_policy}')


def test_grant_all_on_schema(cur):
    """GRANT ALL ON SCHEMA to a role must work."""
    schema_role = 'skill_test_schema_role'
    run_sql(cur, f'CREATE ROLE IF NOT EXISTS {schema_role}')
    run_sql(cur, f'GRANT ALL ON SCHEMA {SCHEMA} TO ROLE {schema_role}')
    run_sql(cur, f'DROP ROLE IF EXISTS {schema_role}')
