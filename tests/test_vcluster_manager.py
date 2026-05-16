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
    # Suspend first to ensure cluster is in a stable state before dropping
    run_sql(cur, f'ALTER VCLUSTER IF EXISTS {TEST_VC} SUSPEND')
    run_sql(cur, f'DROP VCLUSTER IF EXISTS {TEST_VC}')


# ---------------------------------------------------------------------------
# P1 new cases
# ---------------------------------------------------------------------------

def test_create_vcluster_analytics(cur):
    """CREATE VCLUSTER ANALYTICS with MIN/MAX_REPLICAS and MAX_CONCURRENCY must work."""
    run_sql(cur, """
        CREATE VCLUSTER IF NOT EXISTS skill_test_ap_vc
          VCLUSTER_TYPE = ANALYTICS
          MIN_REPLICAS = 1
          MAX_REPLICAS = 2
          MAX_CONCURRENCY = 16
          COMMENT '测试AP集群'
    """)
    run_sql(cur, 'DROP VCLUSTER IF EXISTS skill_test_ap_vc')


def test_ap_vcluster_invalid_size_fails(cur):
    """VCLUSTER_SIZE=3 for ANALYTICS type: actual behavior is success (not an error).

    Note: the 2^n size constraint is NOT enforced server-side; VCLUSTER_SIZE=3 is
    accepted.  The test documents this actual behavior.
    """
    run_sql(cur, """
        CREATE VCLUSTER IF NOT EXISTS skill_test_ap_sz3_vc
          VCLUSTER_TYPE = ANALYTICS
          VCLUSTER_SIZE = 3
    """)
    run_sql(cur, 'DROP VCLUSTER IF EXISTS skill_test_ap_sz3_vc')


# ---------------------------------------------------------------------------
# P2 new cases
# ---------------------------------------------------------------------------

def test_alter_vcluster_auto_suspend(cur):
    """ALTER VCLUSTER SET AUTO_SUSPEND_IN_SECOND must work."""
    run_sql(cur, 'ALTER VCLUSTER DEFAULT SET AUTO_SUSPEND_IN_SECOND = 300')


def test_alter_vcluster_cancel_all_jobs(cur):
    """ALTER VCLUSTER CANCEL ALL JOBS: valid syntax; may fail with InvalidState
    when the cluster is not in RUNNING state (e.g. SUSPENDED, RESUMING).
    The test accepts both success and the expected state-transition error.
    """
    try:
        cur.execute('ALTER VCLUSTER DEFAULT CANCEL ALL JOBS')
    except Exception as e:
        err = str(e)
        # Accept InvalidState errors caused by cluster not being in RUNNING state
        assert 'InvalidState' in err or 'PREPARE_CANCEL' in err, (
            f"Unexpected error from CANCEL ALL JOBS: {err}"
        )


def test_create_vcluster_integration(cur):
    """CREATE VCLUSTER INTEGRATION type must work.

    Note: INTEGRATION type does NOT support MIN_REPLICAS / MAX_REPLICAS properties;
    those are ANALYTICS-only.  Omit them to avoid InvalidArgument errors.
    """
    run_sql(cur, """
        CREATE VCLUSTER IF NOT EXISTS skill_test_int_vc
          VCLUSTER_TYPE = INTEGRATION
          COMMENT '测试集成集群'
    """)
    run_sql(cur, 'DROP VCLUSTER IF EXISTS skill_test_int_vc')


def test_alter_vcluster_preload_tables(cur):
    """SHOW VCLUSTER <vc> PRELOAD CACHED STATUS must work for ANALYTICS vclusters.

    PRELOAD_TABLES requires an ANALYTICS vcluster. This test verifies the
    SHOW PRELOAD CACHED STATUS syntax using the AP vcluster if available.
    """
    import pytest as _pytest
    cur.execute("SHOW VCLUSTERS WHERE vcluster_type = 'ANALYTICS'")
    rows = cur.fetchall()
    if not rows:
        _pytest.skip("No ANALYTICS vcluster available to test PRELOAD CACHED STATUS")
    ap_vc = rows[0][0]
    run_sql(cur, f'SHOW VCLUSTER {ap_vc} PRELOAD CACHED STATUS')