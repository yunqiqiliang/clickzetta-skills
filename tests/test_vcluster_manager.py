"""
Validation tests for clickzetta-vcluster-manager skill.

Covers:
- SHOW VCLUSTERS
- SHOW VCLUSTERS WHERE state / vcluster_type
- SHOW VCLUSTERS LIKE pattern
- DESC VCLUSTER / DESC VCLUSTER EXTENDED
- USE VCLUSTER
- CREATE VCLUSTER (GENERAL type)
- ALTER VCLUSTER SUSPEND / RESUME
- ALTER VCLUSTER SET VCLUSTER_SIZE
- ALTER VCLUSTER SET COMMENT
- DROP VCLUSTER IF EXISTS
"""
import os
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
TEST_VC = 'skill_test_vc_tmp'


@pytest.fixture(scope='module', autouse=True)
def cleanup(cur):
    try:
        cur.execute(f'DROP VCLUSTER IF EXISTS {TEST_VC}')
    except Exception:
        pass
    yield
    try:
        cur.execute(f'DROP VCLUSTER IF EXISTS {TEST_VC}')
    except Exception:
        pass


def test_show_vclusters(cur):
    """SHOW VCLUSTERS must work."""
    cur.execute('SHOW VCLUSTERS')
    rows = cur.fetchall()
    assert rows is not None


def test_show_vclusters_where_state(cur):
    """SHOW VCLUSTERS WHERE state must work."""
    run_sql(cur, "SHOW VCLUSTERS WHERE state = 'RUNNING'")


def test_show_vclusters_where_type(cur):
    """SHOW VCLUSTERS WHERE vcluster_type must work."""
    run_sql(cur, "SHOW VCLUSTERS WHERE vcluster_type = 'ANALYTICS'")


def test_show_vclusters_like(cur):
    """SHOW VCLUSTERS LIKE pattern must work."""
    run_sql(cur, "SHOW VCLUSTERS LIKE 'default%'")


def test_desc_vcluster(cur):
    """DESC VCLUSTER must work."""
    vc = os.environ.get('CLICKZETTA_VCLUSTER', 'default_ap')
    run_sql(cur, f'DESC VCLUSTER {vc}')


def test_desc_vcluster_extended(cur):
    """DESC VCLUSTER EXTENDED must work."""
    vc = os.environ.get('CLICKZETTA_VCLUSTER', 'default_ap')
    run_sql(cur, f'DESC VCLUSTER EXTENDED {vc}')


def test_use_vcluster(cur):
    """USE VCLUSTER must work."""
    vc = os.environ.get('CLICKZETTA_VCLUSTER', 'default_ap')
    run_sql(cur, f'USE VCLUSTER {vc}')


def test_create_vcluster_general(cur):
    """CREATE VCLUSTER GENERAL type must work."""
    run_sql(cur, f"""
        CREATE VCLUSTER IF NOT EXISTS {TEST_VC}
          VCLUSTER_TYPE = GENERAL
          VCLUSTER_SIZE = 1
          AUTO_SUSPEND_IN_SECOND = 60
          AUTO_RESUME = TRUE
          COMMENT '测试集群，可删除'
    """)


def test_alter_vcluster_set_comment(cur):
    """ALTER VCLUSTER SET COMMENT must work."""
    run_sql(cur, f"ALTER VCLUSTER IF EXISTS {TEST_VC} SET COMMENT '更新注释'")


def test_alter_vcluster_set_size(cur):
    """ALTER VCLUSTER SET VCLUSTER_SIZE must work."""
    run_sql(cur, f'ALTER VCLUSTER IF EXISTS {TEST_VC} SET VCLUSTER_SIZE = 2')


def test_alter_vcluster_suspend(cur):
    """ALTER VCLUSTER SUSPEND must work."""
    run_sql(cur, f'ALTER VCLUSTER IF EXISTS {TEST_VC} SUSPEND')


def test_alter_vcluster_resume(cur):
    """ALTER VCLUSTER RESUME must work."""
    run_sql(cur, f'ALTER VCLUSTER IF EXISTS {TEST_VC} RESUME')


def test_drop_vcluster(cur):
    """DROP VCLUSTER IF EXISTS must work."""
    run_sql(cur, f'DROP VCLUSTER IF EXISTS {TEST_VC}')
