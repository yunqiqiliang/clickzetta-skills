"""

Validation tests for clickzetta-dynamic-table skill.

Covers:
- CREATE DYNAMIC TABLE with PROPERTIES syntax
- CREATE DYNAMIC TABLE with REFRESH interval VCLUSTER syntax
- ALTER DYNAMIC TABLE SUSPEND / RESUME
- ALTER DYNAMIC TABLE SET PROPERTIES (target_lag)
- SHOW TABLES WHERE is_dynamic
- SHOW DYNAMIC TABLE REFRESH HISTORY
- DROP DYNAMIC TABLE
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
DT_PROPS = f'{SCHEMA}.dt_validate_props'
DT_REFRESH = f'{SCHEMA}.dt_validate_refresh'
SRC = f'{SCHEMA}.dt_src'


@pytest.fixture(scope='module', autouse=True)
def setup_source(cur):
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SRC} (id INT, val STRING)')
    run_sql(cur, f"INSERT INTO {SRC} VALUES (1, 'a')")
    yield
    run_sql(cur, f'DROP TABLE IF EXISTS {SRC}')


@pytest.fixture(scope='module', autouse=True)
def cleanup(cur, setup_source):
    yield
    for t in [DT_PROPS, DT_REFRESH]:
        try:
            cur.execute(f'DROP DYNAMIC TABLE IF EXISTS {t}')
        except Exception:
            pass


def test_create_with_properties_syntax(cur):
    """PROPERTIES ('target_lag'=..., 'warehouse'=...) syntax must work."""
    run_sql(cur, f"""
        CREATE DYNAMIC TABLE IF NOT EXISTS {DT_PROPS}
          PROPERTIES ('target_lag' = '1 hour', 'warehouse' = 'default_ap')
        AS SELECT id, val FROM {SRC}
    """)


def test_create_with_refresh_interval_syntax(cur):
    """REFRESH interval N MINUTE VCLUSTER syntax must work."""
    run_sql(cur, f"""
        CREATE OR REPLACE DYNAMIC TABLE {DT_REFRESH}
          REFRESH interval 1 MINUTE
          VCLUSTER default_ap
        AS SELECT id, val FROM {SRC}
    """)


def test_show_tables_where_is_dynamic(cur):
    """SHOW TABLES IN schema WHERE is_dynamic must return results."""
    cur.execute(f'SHOW TABLES IN {SCHEMA} WHERE is_dynamic')
    rows = cur.fetchall()
    names = [str(r[1]).lower() for r in rows]
    assert any('dt_validate' in n for n in names), \
        f"Expected dynamic tables in result, got: {names}"


def test_show_tables_where_is_dynamic_no_schema(cur):
    """SHOW TABLES WHERE is_dynamic (current schema) must not error."""
    run_sql(cur, 'SHOW TABLES WHERE is_dynamic')


def test_alter_suspend_resume(cur):
    """SUSPEND and RESUME must work."""
    run_sql(cur, f'ALTER DYNAMIC TABLE {DT_PROPS} SUSPEND')
    run_sql(cur, f'ALTER DYNAMIC TABLE {DT_PROPS} RESUME')


def test_alter_set_properties_target_lag(cur):
    """SET PROPERTIES to change target_lag must work."""
    run_sql(cur, f"ALTER DYNAMIC TABLE {DT_PROPS} SET PROPERTIES ('target_lag' = '2 hours')")


def test_show_refresh_history(cur):
    """SHOW DYNAMIC TABLE REFRESH HISTORY must not error."""
    run_sql(cur, f'SHOW DYNAMIC TABLE REFRESH HISTORY FOR {DT_PROPS}')


def test_desc_dynamic_table(cur):
    """DESC DYNAMIC TABLE must not error."""
    run_sql(cur, f'DESC DYNAMIC TABLE {DT_PROPS}')


def test_drop_dynamic_table(cur):
    """DROP DYNAMIC TABLE IF EXISTS must work."""
    run_sql(cur, f'DROP DYNAMIC TABLE IF EXISTS {DT_PROPS}')
    run_sql(cur, f'DROP DYNAMIC TABLE IF EXISTS {DT_REFRESH}')


def test_target_lag_snowflake_style_fails(cur):
    """Snowflake-style TARGET_LAG = '1 hour' must NOT work (wrong syntax)."""
    err = run_sql(cur, f"""
        CREATE DYNAMIC TABLE IF NOT EXISTS {SCHEMA}.dt_wrong_syntax
          TARGET_LAG = '1 hour'
        AS SELECT id FROM {SRC}
    """, expect_error=True)
    assert err, "Expected syntax error for Snowflake-style TARGET_LAG"
    try:
        cur.execute(f'DROP DYNAMIC TABLE IF EXISTS {SCHEMA}.dt_wrong_syntax')
    except Exception:
        pass
