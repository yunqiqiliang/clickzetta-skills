"""

Validation tests for clickzetta-dynamic-table skill.

Covers:
- CREATE DYNAMIC TABLE with PROPERTIES syntax
- CREATE DYNAMIC TABLE with REFRESH interval VCLUSTER syntax (GP vcluster 'default')
- ALTER DYNAMIC TABLE SUSPEND / RESUME
- ALTER DYNAMIC TABLE SET PROPERTIES (target_lag)
- SHOW TABLES WHERE is_dynamic
- SHOW DYNAMIC TABLE REFRESH HISTORY
- DROP DYNAMIC TABLE
- REFRESH DYNAMIC TABLE (manual trigger)
- SHOW TABLES column name is table_name (not name)
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
    """REFRESH interval N MINUTE VCLUSTER syntax must work.

    SKILL.md requires GP-type vcluster ('default'), not AP-type ('default_ap').
    AP-type clusters do not support small-file compaction and degrade query
    performance over time.  See CLAUDE.md common-errors table.
    """
    run_sql(cur, f"""
        CREATE OR REPLACE DYNAMIC TABLE {DT_REFRESH}
          REFRESH interval 1 MINUTE
          VCLUSTER default
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


def test_refresh_dynamic_table(cur):
    """REFRESH DYNAMIC TABLE schema.table must succeed.

    Verified 2026-05-16: REFRESH DYNAMIC TABLE is the correct manual-trigger
    syntax per SKILL.md.  The command succeeds when the target is a valid
    Dynamic Table.  (Contrast with ALTER DYNAMIC TABLE ... REFRESH which is
    documented as wrong syntax in SKILL.md.)
    """
    run_sql(cur, f'REFRESH DYNAMIC TABLE {DT_REFRESH}')


def test_alter_dynamic_table_refresh_does_not_error(cur):
    """ALTER DYNAMIC TABLE t REFRESH does not raise a syntax error.

    SKILL.md documents 'ALTER DYNAMIC TABLE ... REFRESH' as wrong syntax and
    recommends 'REFRESH DYNAMIC TABLE ...' instead.  However, empirical testing
    (2026-05-16) shows the ALTER form is accepted by the parser and returns
    OPERATION SUCCEED even on a regular table — it does NOT raise an error.

    This test documents the actual runtime behaviour so that the skill guidance
    (prefer REFRESH DYNAMIC TABLE) is understood as a best-practice
    recommendation, not a hard syntax restriction.
    """
    # DT_REFRESH was created in test_create_with_refresh_interval_syntax.
    # ALTER DYNAMIC TABLE ... REFRESH succeeds (no error) — document this fact.
    run_sql(cur, f'ALTER DYNAMIC TABLE {DT_REFRESH} REFRESH')


def test_show_tables_column_name_is_table_name(cur):
    """SHOW TABLES result column is 'table_name', not 'name'.

    Verified 2026-05-16:
    - SHOW TABLES returns columns: schema_name, table_name, is_view,
      is_materialized_view, is_external, is_dynamic
    - WHERE table_name = 'x' works correctly
    - WHERE name = 'x' raises a semantic error (cannot resolve column 'name')

    SKILL.md and CLAUDE.md both document this as a common pitfall.
    """
    # Correct column name: table_name
    cur.execute(f'SHOW TABLES IN {SCHEMA} WHERE table_name = \'dt_src\'')
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    assert 'table_name' in cols, f"Expected 'table_name' column, got: {cols}"
    assert 'name' not in cols, f"Unexpected 'name' column found: {cols}"

    # Wrong column name: 'name' must raise an error
    err = run_sql(
        cur,
        f"SHOW TABLES IN {SCHEMA} WHERE name = 'dt_src'",
        expect_error=True,
    )
    assert err, "Expected error when filtering SHOW TABLES by 'name' column"
    assert 'name' in err.lower() or 'column' in err.lower(), \
        f"Error message should mention column resolution, got: {err}"
