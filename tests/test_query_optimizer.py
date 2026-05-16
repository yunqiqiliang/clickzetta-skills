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
        (1, 'A', 100.0, DATE '2024-01-01'),
        (2, 'B', 200.0, DATE '2024-01-02'),
        (3, 'A', 150.0, DATE '2024-01-03')
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


# ---------------------------------------------------------------------------
# P1 new cases
# ---------------------------------------------------------------------------

def test_optimize_table(cur):
    """OPTIMIZE table must work (returns 'No compaction job generated' when
    no files need compaction)."""
    run_sql(cur, f'OPTIMIZE {T}')


def test_optimize_with_partition_filter(cur):
    """OPTIMIZE with WHERE on a transform-based partition (days(dt)) fails.

    Note: OPTIMIZE WHERE cannot resolve the original column 'dt' when the
    partition is defined as a transform (days(dt)).  This is a known limitation;
    the test documents the actual error behavior.
    """
    T_PART = f'{SCHEMA}.opt_part_test'
    run_sql(cur, f'DROP TABLE IF EXISTS {T_PART}')
    run_sql(cur, f"""
        CREATE TABLE IF NOT EXISTS {T_PART} (id INT, dt DATE)
          PARTITIONED BY (days(dt))
    """)
    run_sql(cur, f"INSERT INTO {T_PART} VALUES (1, DATE '2024-01-01')")
    # Partition column 'dt' cannot be resolved in OPTIMIZE WHERE for transforms
    err = run_sql(cur, f"OPTIMIZE {T_PART} WHERE dt = DATE '2024-01-01'",
                  expect_error=True)
    assert err, "Expected OPTIMIZE WHERE on transform partition to fail"
    run_sql(cur, f'DROP TABLE IF EXISTS {T_PART}')


# ---------------------------------------------------------------------------
# P2 new cases
# ---------------------------------------------------------------------------

def test_explain_output_contains_scan(cur):
    """EXPLAIN output must contain 'Scan' or 'TableScan' (case-insensitive)."""
    cur.execute(f'EXPLAIN SELECT id FROM {T} WHERE id = 1')
    rows = cur.fetchall()
    explain_text = ' '.join(str(r) for r in rows)
    assert 'scan' in explain_text.lower(), (
        f"Expected 'scan' keyword in EXPLAIN output, got: {explain_text[:300]}"
    )


def test_alter_table_apply_sort_key(cur):
    """ALTER TABLE SET PROPERTIES hint.sort.columns must work."""
    run_sql(cur, f'ALTER TABLE {T} SET PROPERTIES("hint.sort.columns"="id")')
