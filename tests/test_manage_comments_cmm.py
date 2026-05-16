"""
Additional validation tests for clickzetta-manage-comments skill.

Uses isolated schema skill_test_cmm to avoid conflicts with concurrent agents.
Covers:
- ALTER VCLUSTER SET COMMENT (add/clear)
- SHOW CREATE TABLE verifies comment content
- ALTER MATERIALIZED VIEW SET COMMENT (add/clear)
- COMMENT ON SCHEMA IS '...' must fail (wrong syntax)
"""
import pytest
from conftest import run_sql

CMM_SCHEMA = 'skill_test_cmm'
CMM_T = f'{CMM_SCHEMA}.cmm_test'
CMM_MV_SRC = f'{CMM_SCHEMA}.cmm_mv_src'
CMM_MV = f'{CMM_SCHEMA}.cmm_mv'


@pytest.fixture(scope='module', autouse=True)
def cmm_setup(cur):
    """Set up isolated objects in skill_test_cmm."""
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {CMM_SCHEMA}')
    run_sql(cur, f'DROP TABLE IF EXISTS {CMM_T}')
    run_sql(cur, f'CREATE TABLE {CMM_T} (id INT)')
    run_sql(cur, f'DROP TABLE IF EXISTS {CMM_MV_SRC}')
    run_sql(cur, f'CREATE TABLE {CMM_MV_SRC} (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {CMM_MV_SRC} VALUES (1, 'a')")
    run_sql(cur, f'DROP MATERIALIZED VIEW IF EXISTS {CMM_MV}')
    run_sql(cur, f"""
        CREATE MATERIALIZED VIEW {CMM_MV}
          REFRESH INTERVAL 60 MINUTE vcluster DEFAULT
        AS SELECT id, val FROM {CMM_MV_SRC}
    """)
    yield
    for obj in [CMM_T, CMM_MV_SRC]:
        try:
            cur.execute(f'DROP TABLE IF EXISTS {obj}')
        except Exception:
            pass
    try:
        cur.execute(f'DROP MATERIALIZED VIEW IF EXISTS {CMM_MV}')
    except Exception:
        pass
    try:
        cur.execute(f'DROP SCHEMA IF EXISTS {CMM_SCHEMA} CASCADE')
    except Exception:
        pass


def test_alter_vcluster_set_comment(cur):
    """ALTER VCLUSTER DEFAULT SET COMMENT must work (or skip if cluster is scaling)."""
    try:
        run_sql(cur, "ALTER VCLUSTER DEFAULT SET COMMENT '测试集群注释'")
        run_sql(cur, "ALTER VCLUSTER DEFAULT SET COMMENT ''")
    except Exception as e:
        if 'SCALING_UP' in str(e) or 'InvalidState' in str(e):
            pytest.skip(f"Cluster is scaling, skipping vcluster comment test: {e}")
        raise


def test_desc_verifies_comment_content(cur):
    """SHOW CREATE TABLE must include the comment text set via ALTER TABLE SET COMMENT."""
    run_sql(cur, f"ALTER TABLE {CMM_T} SET COMMENT '验证注释内容'")
    cur.execute(f'SHOW CREATE TABLE {CMM_T}')
    rows = cur.fetchall()
    assert rows, "SHOW CREATE TABLE returned no rows"
    ddl_text = str(rows)
    assert '验证注释内容' in ddl_text, \
        f"Expected '验证注释内容' in SHOW CREATE TABLE output, got: {ddl_text[:500]}"


def test_alter_materialized_view_comment(cur):
    """ALTER MATERIALIZED VIEW SET COMMENT must work (add and clear)."""
    run_sql(cur, f"ALTER MATERIALIZED VIEW {CMM_MV} SET COMMENT '物化视图注释'")
    run_sql(cur, f"ALTER MATERIALIZED VIEW {CMM_MV} SET COMMENT ''")


def test_comment_on_schema_fails(cur):
    """COMMENT ON SCHEMA IS '...' must fail (ClickZetta does not support this syntax)."""
    err = run_sql(cur, f"COMMENT ON SCHEMA {CMM_SCHEMA} IS '标准SQL注释语法'", expect_error=True)
    assert err, "Expected syntax error for COMMENT ON SCHEMA IS '...'"


def test_alter_workspace_set_comment(cur):
    """ALTER WORKSPACE SET COMMENT / empty comment must work."""
    run_sql(cur, "ALTER WORKSPACE quick_start SET COMMENT '测试注释'")
    run_sql(cur, "ALTER WORKSPACE quick_start SET COMMENT ''")


def test_create_or_replace_view_with_comment(cur):
    """VIEW comment must be set via CREATE OR REPLACE VIEW ... COMMENT '...'."""
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {CMM_SCHEMA}.view_src_p3 (id INT, val STRING)')
    run_sql(cur, f"""
        CREATE OR REPLACE VIEW {CMM_SCHEMA}.view_p3_comment
          COMMENT '视图注释内容'
        AS SELECT id, val FROM {CMM_SCHEMA}.view_src_p3
    """)
    cur.execute(f'SHOW CREATE TABLE {CMM_SCHEMA}.view_p3_comment')
    rows = cur.fetchall()
    assert rows, "SHOW CREATE TABLE should return DDL"
    ddl = str(rows)
    assert '视图注释内容' in ddl, f"Expected comment in DDL, got: {ddl[:200]}"
    run_sql(cur, f'DROP VIEW IF EXISTS {CMM_SCHEMA}.view_p3_comment')
    run_sql(cur, f'DROP TABLE IF EXISTS {CMM_SCHEMA}.view_src_p3')
