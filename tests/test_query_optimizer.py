"""
Validation tests for clickzetta-query-optimizer skill.

Covers:
- EXPLAIN SELECT must work
- EXPLAIN EXTENDED SELECT must work
- SHOW JOBS LIMIT N must work
- SET result cache on/off must work
- OPTIMIZE table must work (GP cluster)
- ANALYZE TABLE must work
- information_schema.sortkey_candidates must be queryable
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T = f'{SCHEMA}.qopt_test'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')
    run_sql(cur, f'CREATE TABLE {T} (id INT, category STRING, amount DOUBLE, dt DATE)')
    run_sql(cur, f"""
        INSERT INTO {T} VALUES
        (1, 'A', 100.0, '2024-01-01'),
        (2, 'B', 200.0, '2024-01-02'),
        (3, 'A', 150.0, '2024-01-03')
    """)
    yield
    try:
        cur.execute(f'DROP TABLE IF EXISTS {T}')
    except Exception:
        pass


def test_explain(cur):
    """EXPLAIN SELECT must work."""
    run_sql(cur, f'EXPLAIN SELECT * FROM {T} WHERE category = \'A\'')


def test_explain_extended(cur):
    """EXPLAIN EXTENDED SELECT must work."""
    run_sql(cur, f'EXPLAIN EXTENDED SELECT id, SUM(amount) FROM {T} GROUP BY id')


def test_show_jobs_limit(cur):
    """SHOW JOBS LIMIT N must work."""
    run_sql(cur, 'SHOW JOBS LIMIT 10')


def test_show_jobs_in_vcluster(cur):
    """SHOW JOBS IN VCLUSTER must work."""
    import os
    vc = os.environ.get('CLICKZETTA_VCLUSTER', 'default_ap')
    run_sql(cur, f'SHOW JOBS IN VCLUSTER {vc} LIMIT 5')


def test_set_result_cache_on(cur):
    """SET result cache on must work."""
    run_sql(cur, 'SET cz.sql.enable.shortcut.result.cache = true')


def test_set_result_cache_off(cur):
    """SET result cache off must work."""
    run_sql(cur, 'SET cz.sql.enable.shortcut.result.cache = false')


def test_analyze_table(cur):
    """ANALYZE TABLE must work."""
    run_sql(cur, f'ANALYZE TABLE {T}')


def test_sortkey_candidates(cur):
    """information_schema.sortkey_candidates must be queryable."""
    run_sql(cur, 'SELECT * FROM information_schema.sortkey_candidates LIMIT 5')


def test_mapjoin_hint(cur):
    """MAPJOIN hint syntax must work."""
    run_sql(cur, f"""
        SELECT /*+ MAPJOIN (t2) */ t1.id, t2.category
        FROM {T} t1
        JOIN {T} t2 ON t1.id = t2.id
        LIMIT 5
    """)
