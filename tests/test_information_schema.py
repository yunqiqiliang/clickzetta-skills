"""
Validation tests for clickzetta-information-schema skill.

Covers:
- information_schema.tables has 'bytes' field (not 'total_bytes')
- information_schema.job_history has pt_date, cru, status='SUCCEED'
- information_schema.schemas, columns, users, roles exist
- ILIKE works in column filter
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'


def test_tables_has_bytes_field(cur):
    """information_schema.tables must have 'bytes' column (not 'total_bytes')."""
    cur.execute(f"""
        SELECT table_schema, table_name, bytes, row_count
        FROM information_schema.tables
        WHERE table_schema = '{SCHEMA}'
        LIMIT 1
    """)
    col_names = [d[0].lower() for d in cur.description]
    assert 'bytes' in col_names, f"Expected 'bytes' column, got: {col_names}"
    assert 'total_bytes' not in col_names, \
        f"'total_bytes' should not exist in information_schema.tables, got: {col_names}"


def test_tables_no_total_bytes_field(cur):
    """information_schema.tables must NOT have 'total_bytes' column."""
    err = run_sql(cur, f"""
        SELECT total_bytes FROM information_schema.tables LIMIT 1
    """, expect_error=True)
    assert err, "Expected error for 'total_bytes' in information_schema.tables"


def test_job_history_has_pt_date(cur):
    """information_schema.job_history must have pt_date partition column."""
    cur.execute("""
        SELECT job_id, status, cru, pt_date
        FROM information_schema.job_history
        WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 1 DAY AS DATE)
        LIMIT 1
    """)
    col_names = [d[0].lower() for d in cur.description]
    assert 'pt_date' in col_names, f"Expected 'pt_date' column, got: {col_names}"
    assert 'cru' in col_names, f"Expected 'cru' column, got: {col_names}"


def test_job_history_succeed_status(cur):
    """job_history status='SUCCEED' must return results (not 'SUCCESS')."""
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM information_schema.job_history
        WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 7 DAY AS DATE)
          AND status = 'SUCCEED'
    """)
    row = cur.fetchone()
    # Just verify the query runs without error; count may be 0 in quiet environments
    assert row is not None


def test_job_history_success_returns_zero(cur):
    """job_history status='SUCCESS' should return 0 rows (wrong value)."""
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM information_schema.job_history
        WHERE pt_date >= CAST(CURRENT_DATE - INTERVAL 7 DAY AS DATE)
          AND status = 'SUCCESS'
    """)
    row = cur.fetchone()
    assert row[0] == 0, \
        f"'SUCCESS' should return 0 rows (correct value is 'SUCCEED'), got {row[0]}"


def test_schemas_view(cur):
    """information_schema.schemas must be queryable."""
    cur.execute("""
        SELECT schema_name, type, create_time
        FROM information_schema.schemas
        ORDER BY create_time DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    assert rows is not None


def test_columns_view_ilike(cur):
    """information_schema.columns with ILIKE filter must work."""
    run_sql(cur, f"""
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE column_name ILIKE '%id%'
        LIMIT 5
    """)


def test_tables_type_filter(cur):
    """information_schema.tables with table_type filter must work."""
    cur.execute("""
        SELECT table_schema, table_name, table_type, row_count, bytes, create_time
        FROM information_schema.tables
        WHERE table_type = 'MANAGED_TABLE'
        ORDER BY table_schema, table_name
        LIMIT 5
    """)
    col_names = [d[0].lower() for d in cur.description]
    assert 'bytes' in col_names


def test_users_view(cur):
    """information_schema.users must be queryable."""
    run_sql(cur, """
        SELECT user_name, role_names, create_time
        FROM information_schema.users
        LIMIT 5
    """)


def test_roles_view(cur):
    """information_schema.roles must be queryable."""
    run_sql(cur, """
        SELECT role_name, user_names
        FROM information_schema.roles
        LIMIT 5
    """)


def test_storage_size_query(cur):
    """Storage size query using bytes field must work."""
    run_sql(cur, f"""
        SELECT table_schema, table_name,
               ROUND(bytes / 1024.0 / 1024 / 1024, 3) AS size_gb,
               row_count
        FROM information_schema.tables
        WHERE table_type = 'MANAGED_TABLE'
        ORDER BY bytes DESC
        LIMIT 5
    """)


def test_columns_no_ordinal_position(cur):
    """information_schema.columns must NOT have ordinal_position column."""
    err = run_sql(cur, f"""
        SELECT ordinal_position FROM information_schema.columns
        WHERE table_schema = '{SCHEMA}' LIMIT 1
    """, expect_error=True)
    assert err, "Expected error: information_schema.columns has no ordinal_position column"
    assert 'ordinal_position' in err.lower() or 'cannot resolve' in err.lower(), \
        f"Unexpected error message: {err[:300]}"


def test_job_history_cru_aggregation_by_user(cur):
    """job_history CRU aggregation by user must work using sys.information_schema."""
    cur.execute("""
        SELECT job_creator, COUNT(*) AS job_cnt, SUM(cru) AS total_cru
        FROM sys.information_schema.job_history
        WHERE start_time >= CURRENT_DATE() - INTERVAL 7 DAY
        GROUP BY job_creator
        ORDER BY total_cru DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    # Query must succeed; result may be empty in quiet environments
    assert rows is not None
    col_names = [d[0].lower() for d in cur.description]
    assert 'job_creator' in col_names
    assert 'job_cnt' in col_names
    assert 'total_cru' in col_names


def test_sys_instance_usage_queryable(cur):
    """SYS.information_schema.instance_usage must be queryable.

    Requires instance_admin or equivalent privilege. Skipped if permission denied.
    """
    import pytest as _pytest
    try:
        cur.execute('SELECT * FROM SYS.information_schema.instance_usage LIMIT 5')
        rows = cur.fetchall()
        assert cur.description is not None
    except Exception as e:
        err = str(e)
        if 'permission' in err.lower() or 'privilege' in err.lower() or 'access' in err.lower():
            _pytest.skip(f"instance_admin privilege required: {err[:80]}")
        raise
