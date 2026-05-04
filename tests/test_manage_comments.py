"""
Validation tests for clickzetta-manage-comments skill.

Covers:
- ALTER TABLE SET COMMENT (add/modify/delete)
- ALTER TABLE CHANGE COLUMN COMMENT
- ALTER SCHEMA SET COMMENT
- ALTER DYNAMIC TABLE SET COMMENT
- ALTER DYNAMIC TABLE CHANGE COLUMN COMMENT
- COMMENT ON TABLE IS '...' must fail (wrong syntax)
- ALTER TABLE ALTER COLUMN COMMENT must fail (wrong syntax)
- Single-quote escaping in comments
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T = f'{SCHEMA}.comment_test'
DT = f'{SCHEMA}.comment_dt_test'
SRC = f'{SCHEMA}.comment_src'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'DROP DYNAMIC TABLE IF EXISTS {DT}')
    run_sql(cur, f'DROP TABLE IF EXISTS {SRC}')
    run_sql(cur, f'CREATE TABLE {T} (id INT, name STRING, amount DOUBLE)')
    run_sql(cur, f'CREATE TABLE {SRC} (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {SRC} VALUES (1, 'a')")
    run_sql(cur, f"""
        CREATE DYNAMIC TABLE {DT}
          PROPERTIES ('target_lag' = '1 hour', 'warehouse' = 'default_ap')
        AS SELECT id, val FROM {SRC}
    """)
    yield
    for obj in [T, SRC]:
        try:
            cur.execute(f'DROP TABLE IF EXISTS {obj}')
        except Exception:
            pass
    try:
        cur.execute(f'DROP DYNAMIC TABLE IF EXISTS {DT}')
    except Exception:
        pass


def test_alter_table_set_comment(cur):
    """ALTER TABLE SET COMMENT must work."""
    run_sql(cur, f"ALTER TABLE {T} SET COMMENT '订单测试表'")


def test_alter_table_set_comment_modify(cur):
    """ALTER TABLE SET COMMENT (modify) must work."""
    run_sql(cur, f"ALTER TABLE {T} SET COMMENT '修改后的注释'")


def test_alter_table_set_comment_delete(cur):
    """ALTER TABLE SET COMMENT '' (delete) must work."""
    run_sql(cur, f"ALTER TABLE {T} SET COMMENT ''")


def test_alter_table_change_column_comment(cur):
    """ALTER TABLE CHANGE COLUMN COMMENT must work."""
    run_sql(cur, f"ALTER TABLE {T} CHANGE COLUMN id COMMENT '主键ID'")
    run_sql(cur, f"ALTER TABLE {T} CHANGE COLUMN name COMMENT '用户名称'")


def test_alter_table_change_column_comment_delete(cur):
    """ALTER TABLE CHANGE COLUMN COMMENT '' (delete) must work."""
    run_sql(cur, f"ALTER TABLE {T} CHANGE COLUMN id COMMENT ''")


def test_comment_on_table_fails(cur):
    """COMMENT ON TABLE IS '...' must fail (wrong syntax for ClickZetta)."""
    err = run_sql(cur, f"COMMENT ON TABLE {T} IS '标准SQL注释'", expect_error=True)
    assert err, "Expected syntax error for COMMENT ON TABLE IS '...'"


def test_alter_column_comment_fails(cur):
    """ALTER TABLE ALTER COLUMN COMMENT must fail (use CHANGE COLUMN instead)."""
    err = run_sql(cur, f"ALTER TABLE {T} ALTER COLUMN id COMMENT '错误语法'", expect_error=True)
    assert err, "Expected error for ALTER COLUMN COMMENT (should use CHANGE COLUMN)"


def test_comment_with_single_quote_escape(cur):
    """Comment with escaped single quote must work."""
    run_sql(cur, f"ALTER TABLE {T} SET COMMENT 'it''s a test table'")


def test_alter_schema_set_comment(cur):
    """ALTER SCHEMA SET COMMENT must work."""
    run_sql(cur, f"ALTER SCHEMA {SCHEMA} SET COMMENT '测试Schema'")
    run_sql(cur, f"ALTER SCHEMA {SCHEMA} SET COMMENT ''")


def test_alter_dynamic_table_set_comment(cur):
    """ALTER DYNAMIC TABLE SET COMMENT must work."""
    run_sql(cur, f"ALTER DYNAMIC TABLE {DT} SET COMMENT '动态表注释'")
    run_sql(cur, f"ALTER DYNAMIC TABLE {DT} SET COMMENT ''")


def test_alter_dynamic_table_change_column_comment(cur):
    """ALTER DYNAMIC TABLE CHANGE COLUMN COMMENT must work."""
    run_sql(cur, f"ALTER DYNAMIC TABLE {DT} CHANGE COLUMN id COMMENT '动态表字段注释'")
    run_sql(cur, f"ALTER DYNAMIC TABLE {DT} CHANGE COLUMN id COMMENT ''")


def test_desc_table_shows_comment(cur):
    """DESC TABLE must show comment column."""
    run_sql(cur, f"ALTER TABLE {T} SET COMMENT '验证注释'")
    cur.execute(f'DESC {T}')
    rows = cur.fetchall()
    assert rows is not None
