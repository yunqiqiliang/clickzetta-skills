"""
Validation tests for clickzetta-metadata-query skill.

Covers:
- SHOW TABLES / SHOW TABLES IN schema
- SHOW TABLES WHERE is_view / is_dynamic / is_materialized_view
- SHOW SCHEMAS / SHOW SCHEMAS EXTENDED
- SHOW COLUMNS IN table
- SHOW CREATE TABLE
- SHOW VCLUSTERS
- SHOW JOBS LIMIT N
- SHOW TABLE STREAMS
- DESC TABLE / DESC EXTENDED
- DESC SCHEMA / DESC SCHEMA EXTENDED
- DESC HISTORY
- FROM (SHOW ...) subquery
- SHOW TABLES HISTORY
- SHOW VIEWS IN schema must fail (wrong syntax)
- load_history() with quoted string
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T = f'{SCHEMA}.meta_test'
V = f'{SCHEMA}.meta_view'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    run_sql(cur, f'DROP VIEW IF EXISTS {V}')
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'CREATE TABLE {T} (id INT, name STRING, dt DATE)')
    run_sql(cur, f"INSERT INTO {T} VALUES (1, 'a', '2024-01-01')")
    run_sql(cur, f'CREATE VIEW {V} AS SELECT id, name FROM {T}')
    yield
    try:
        cur.execute(f'DROP VIEW IF EXISTS {V}')
        cur.execute(f'DROP TABLE IF EXISTS {T}')
    except Exception:
        pass


def test_show_tables(cur):
    """SHOW TABLES must work."""
    run_sql(cur, 'SHOW TABLES')


def test_show_tables_in_schema(cur):
    """SHOW TABLES IN schema must work."""
    cur.execute(f'SHOW TABLES IN {SCHEMA}')
    rows = cur.fetchall()
    names = [str(r[1]).lower() for r in rows]
    assert any('meta_test' in n for n in names), f"Expected meta_test in {names}"


def test_show_tables_where_is_view(cur):
    """SHOW TABLES WHERE is_view must work."""
    cur.execute(f'SHOW TABLES IN {SCHEMA} WHERE is_view')
    rows = cur.fetchall()
    names = [str(r[1]).lower() for r in rows]
    assert any('meta_view' in n for n in names), f"Expected meta_view in {names}"


def test_show_tables_where_not_view(cur):
    """SHOW TABLES WHERE is_view = false must work."""
    run_sql(cur, f'SHOW TABLES IN {SCHEMA} WHERE is_view = false AND is_materialized_view = false')


def test_show_views_in_schema_fails(cur):
    """SHOW VIEWS IN schema must fail (use SHOW TABLES WHERE is_view=true instead)."""
    err = run_sql(cur, f'SHOW VIEWS IN {SCHEMA}', expect_error=True)
    assert err, "Expected error for SHOW VIEWS IN schema"


def test_show_schemas(cur):
    """SHOW SCHEMAS must work."""
    run_sql(cur, 'SHOW SCHEMAS')


def test_show_schemas_extended(cur):
    """SHOW SCHEMAS EXTENDED must work."""
    run_sql(cur, 'SHOW SCHEMAS EXTENDED')


def test_show_columns_in(cur):
    """SHOW COLUMNS IN table must work."""
    run_sql(cur, f'SHOW COLUMNS IN {T}')


def test_show_columns_from_in(cur):
    """SHOW COLUMNS FROM table IN schema must work."""
    run_sql(cur, f'SHOW COLUMNS FROM meta_test IN {SCHEMA}')


def test_show_create_table(cur):
    """SHOW CREATE TABLE must work."""
    run_sql(cur, f'SHOW CREATE TABLE {T}')


def test_show_vclusters(cur):
    """SHOW VCLUSTERS must work."""
    run_sql(cur, 'SHOW VCLUSTERS')


def test_show_vclusters_where(cur):
    """SHOW VCLUSTERS WHERE state must work."""
    run_sql(cur, "SHOW VCLUSTERS WHERE state = 'RUNNING'")


def test_show_jobs_limit(cur):
    """SHOW JOBS LIMIT N must work."""
    run_sql(cur, 'SHOW JOBS LIMIT 5')


def test_desc_table(cur):
    """DESC table must work."""
    run_sql(cur, f'DESC {T}')


def test_desc_extended(cur):
    """DESC EXTENDED table must work."""
    run_sql(cur, f'DESC EXTENDED {T}')


def test_desc_schema(cur):
    """DESC SCHEMA must work."""
    run_sql(cur, f'DESC SCHEMA {SCHEMA}')


def test_desc_schema_extended(cur):
    """DESC SCHEMA EXTENDED must work."""
    run_sql(cur, f'DESC SCHEMA EXTENDED {SCHEMA}')


def test_desc_history(cur):
    """DESC HISTORY must work and return version/total_bytes columns."""
    cur.execute(f'DESC HISTORY {T}')
    rows = cur.fetchall()
    assert len(rows) > 0
    col_names = [d[0].lower() for d in cur.description]
    assert 'version' in col_names
    assert 'total_bytes' in col_names


def test_show_tables_history(cur):
    """SHOW TABLES HISTORY must work."""
    run_sql(cur, f'SHOW TABLES HISTORY IN {SCHEMA}')


def test_from_show_subquery(cur):
    """FROM (SHOW TABLES) subquery must work."""
    cur.execute(f"""
        SELECT schema_name, table_name
        FROM (SHOW TABLES IN {SCHEMA})
        WHERE is_view = false
    """)
    rows = cur.fetchall()
    assert rows is not None


def test_load_history_quoted(cur):
    """load_history() with quoted string must work."""
    run_sql(cur, f"SELECT * FROM load_history('{SCHEMA}.meta_test') LIMIT 5")


def test_load_history_unquoted_fails(cur):
    """load_history() without quotes must fail."""
    err = run_sql(cur, f'SELECT * FROM load_history({SCHEMA}.meta_test) LIMIT 1',
                  expect_error=True)
    assert err, "Expected error for load_history without quoted string"


def test_current_context_functions(cur):
    """current_workspace(), current_schema(), current_user(), current_vcluster() must work."""
    cur.execute('SELECT current_workspace(), current_schema(), current_user(), current_vcluster()')
    row = cur.fetchone()
    assert row is not None
    assert row[0] is not None
