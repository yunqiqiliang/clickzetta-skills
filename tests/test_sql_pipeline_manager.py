"""
Validation tests for clickzetta-sql-pipeline-manager skill.

Covers:
- CREATE DYNAMIC TABLE with REFRESH interval VCLUSTER syntax
- CREATE MATERIALIZED VIEW with REFRESH AUTO EVERY syntax
- REFRESH MATERIALIZED VIEW (manual)
- CREATE TABLE STREAM with PROPERTIES
- SHOW TABLES WHERE is_dynamic / is_materialized_view
- SHOW DYNAMIC TABLE REFRESH HISTORY
- ALTER DYNAMIC TABLE SUSPEND / RESUME
- SHOW TABLE STREAMS
- SHOW PIPES
- Snowflake-style TARGET_LAG must fail
- Snowflake-style WAREHOUSE = must fail
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
SRC = f'{SCHEMA}.pipeline_src'
DT = f'{SCHEMA}.pipeline_dt'
MV = f'{SCHEMA}.pipeline_mv'
STREAM = f'{SCHEMA}.pipeline_stream'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    run_sql(cur, f'DROP DYNAMIC TABLE IF EXISTS {DT}')
    run_sql(cur, f'DROP MATERIALIZED VIEW IF EXISTS {MV}')
    run_sql(cur, f'DROP TABLE STREAM IF EXISTS {STREAM}')
    run_sql(cur, f'DROP TABLE IF EXISTS {SRC}')
    run_sql(cur, f'CREATE TABLE {SRC} (id INT, category STRING, amount DOUBLE, dt DATE)')
    run_sql(cur, f"""
        INSERT INTO {SRC} VALUES
        (1, 'A', 100.0, '2024-01-01'),
        (2, 'B', 200.0, '2024-01-02')
    """)
    yield
    for obj, drop in [
        (DT, f'DROP DYNAMIC TABLE IF EXISTS {DT}'),
        (MV, f'DROP MATERIALIZED VIEW IF EXISTS {MV}'),
        (STREAM, f'DROP TABLE STREAM IF EXISTS {STREAM}'),
        (SRC, f'DROP TABLE IF EXISTS {SRC}'),
    ]:
        try:
            cur.execute(drop)
        except Exception:
            pass


def test_create_dynamic_table_refresh_interval(cur):
    """CREATE DYNAMIC TABLE with REFRESH interval VCLUSTER must work."""
    run_sql(cur, f"""
        CREATE OR REPLACE DYNAMIC TABLE {DT}
          REFRESH interval 1 MINUTE
          VCLUSTER default_ap
        AS
        SELECT id, category, SUM(amount) AS total
        FROM {SRC}
        GROUP BY id, category
    """)


def test_dynamic_table_snowflake_target_lag_fails(cur):
    """Snowflake-style TARGET_LAG = '1 minutes' must fail."""
    err = run_sql(cur, f"""
        CREATE DYNAMIC TABLE {SCHEMA}.dt_wrong_tl
          TARGET_LAG = '1 minutes'
          WAREHOUSE = compute_wh
        AS SELECT id FROM {SRC}
    """, expect_error=True)
    assert err, "Expected error for Snowflake-style TARGET_LAG / WAREHOUSE syntax"
    try:
        cur.execute(f'DROP DYNAMIC TABLE IF EXISTS {SCHEMA}.dt_wrong_tl')
    except Exception:
        pass


def test_show_tables_where_is_dynamic(cur):
    """SHOW TABLES WHERE is_dynamic must return the dynamic table."""
    cur.execute(f'SHOW TABLES IN {SCHEMA} WHERE is_dynamic')
    rows = cur.fetchall()
    names = [str(r[1]).lower() for r in rows]
    assert any('pipeline_dt' in n for n in names), f"Expected pipeline_dt in {names}"


def test_show_dynamic_table_refresh_history(cur):
    """SHOW DYNAMIC TABLE REFRESH HISTORY must work."""
    run_sql(cur, f'SHOW DYNAMIC TABLE REFRESH HISTORY {DT} LIMIT 5')


def test_alter_dynamic_table_suspend_resume(cur):
    """ALTER DYNAMIC TABLE SUSPEND / RESUME must work."""
    run_sql(cur, f'ALTER DYNAMIC TABLE {DT} SUSPEND')
    run_sql(cur, f'ALTER DYNAMIC TABLE {DT} RESUME')


def test_create_materialized_view_refresh_auto(cur):
    """CREATE MATERIALIZED VIEW with REFRESH AUTO EVERY must work."""
    run_sql(cur, f"""
        CREATE OR REPLACE MATERIALIZED VIEW {MV}
          COMMENT '测试物化视图'
          REFRESH AUTO EVERY '1 hours'
          VCLUSTER = default_ap
        AS
        SELECT category, SUM(amount) AS total
        FROM {SRC}
        GROUP BY category
    """)


def test_show_tables_where_is_materialized_view(cur):
    """SHOW TABLES WHERE is_materialized_view must return the MV."""
    cur.execute(f'SHOW TABLES IN {SCHEMA} WHERE is_materialized_view')
    rows = cur.fetchall()
    names = [str(r[1]).lower() for r in rows]
    assert any('pipeline_mv' in n for n in names), f"Expected pipeline_mv in {names}"


def test_refresh_materialized_view(cur):
    """REFRESH MATERIALIZED VIEW (manual) must work."""
    run_sql(cur, f'REFRESH MATERIALIZED VIEW {MV}')


def test_create_table_stream_standard(cur):
    """CREATE TABLE STREAM with STANDARD mode must work."""
    run_sql(cur, f"""
        CREATE TABLE STREAM {STREAM}
          ON TABLE {SRC}
          WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD')
    """)


def test_show_table_streams(cur):
    """SHOW TABLE STREAMS must work."""
    run_sql(cur, f'SHOW TABLE STREAMS IN {SCHEMA}')


def test_show_pipes(cur):
    """SHOW PIPES must work."""
    run_sql(cur, 'SHOW PIPES')
