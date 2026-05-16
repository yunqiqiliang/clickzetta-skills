"""
Additional validation tests for clickzetta-metadata-query skill.

Uses isolated schema skill_test_cmm to avoid conflicts with concurrent agents.
Covers:
- SHOW SCHEMAS WHERE schema_type must fail (no such column)
- SHOW VOLUMES IN schema must fail; SHOW VOLUMES WHERE workspace_name works
- SHOW TABLES LIKE '...' WHERE ... must fail (cannot combine)
- SHOW TABLES IN schema WHERE is_dynamic = true
- SHOW PARTITIONS on a partitioned table
- SHOW JOBS ORDER BY must fail
"""
import pytest
from conftest import run_sql

CMM_SCHEMA = 'skill_test_cmm'


@pytest.fixture(scope='module', autouse=True)
def cmm_meta_setup(cur):
    """Set up isolated objects in skill_test_cmm for metadata query tests."""
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {CMM_SCHEMA}')
    run_sql(cur, f'DROP TABLE IF EXISTS {CMM_SCHEMA}.part_test')
    run_sql(cur, f"""
        CREATE TABLE IF NOT EXISTS {CMM_SCHEMA}.part_test
        (id INT, dt DATE)
        PARTITIONED BY (days(dt))
    """)
    run_sql(cur, f"INSERT INTO {CMM_SCHEMA}.part_test VALUES (1, DATE '2024-01-01')")
    yield
    try:
        cur.execute(f'DROP TABLE IF EXISTS {CMM_SCHEMA}.part_test')
    except Exception:
        pass
    try:
        cur.execute(f'DROP SCHEMA IF EXISTS {CMM_SCHEMA} CASCADE')
    except Exception:
        pass


def test_show_schemas_where_fails(cur):
    """SHOW SCHEMAS WHERE schema_type must fail (no schema_type column)."""
    err = run_sql(cur, "SHOW SCHEMAS WHERE schema_type = 'MANAGED'", expect_error=True)
    assert err, "Expected error for SHOW SCHEMAS WHERE schema_type"


def test_show_volumes_in_schema_fails(cur):
    """SHOW VOLUMES IN schema must fail; SHOW VOLUMES WHERE workspace_name must succeed."""
    err = run_sql(cur, f'SHOW VOLUMES IN {CMM_SCHEMA}', expect_error=True)
    assert err, "Expected syntax error for SHOW VOLUMES IN schema"
    # Alternative syntax must work
    run_sql(cur, f"SHOW VOLUMES WHERE workspace_name = '{CMM_SCHEMA}'")


def test_show_tables_like_and_where_fails(cur):
    """SHOW TABLES LIKE '...' WHERE ... must fail (cannot combine LIKE and WHERE)."""
    err = run_sql(cur, "SHOW TABLES LIKE '%test%' WHERE is_view = false", expect_error=True)
    assert err, "Expected syntax error for SHOW TABLES LIKE ... WHERE ..."


def test_show_tables_where_is_dynamic(cur):
    """SHOW TABLES IN schema WHERE is_dynamic = true must work."""
    run_sql(cur, f'SHOW TABLES IN {CMM_SCHEMA} WHERE is_dynamic = true')


def test_show_partitions(cur):
    """SHOW PARTITIONS on a partitioned table must work."""
    cur.execute(f'SHOW PARTITIONS {CMM_SCHEMA}.part_test')
    rows = cur.fetchall()
    assert rows is not None
    # At least one partition should exist after the INSERT
    assert len(rows) >= 1, f"Expected at least 1 partition, got {len(rows)}"


def test_show_jobs_no_order_by_fails(cur):
    """SHOW JOBS ORDER BY must fail (SHOW commands do not support ORDER BY)."""
    err = run_sql(cur, 'SHOW JOBS ORDER BY execution_time LIMIT 5', expect_error=True)
    assert err, "Expected error for SHOW JOBS ORDER BY"
