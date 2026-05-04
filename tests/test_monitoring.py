"""
Validation tests for clickzetta-monitoring skill.

Covers:
- information_schema.tables field names (bytes, NOT total_bytes)
- information_schema.job_history status values (SUCCEED, not SUCCESS)
- SHOW JOBS syntax
- CURRENT_DATE() usage in WHERE
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'


def test_information_schema_tables_bytes_field(cur):
    """information_schema.tables has 'bytes' column, not 'total_bytes'."""
    cur.execute(f"SELECT table_schema, table_name, row_count, bytes FROM information_schema.tables WHERE table_schema = '{SCHEMA}' LIMIT 1")
    # Should not raise


def test_information_schema_tables_no_total_bytes(cur):
    """information_schema.tables does NOT have 'total_bytes' column."""
    run_sql(cur,
        f"SELECT total_bytes FROM information_schema.tables WHERE table_schema = '{SCHEMA}' LIMIT 1",
        expect_error=True
    )


def test_job_history_succeed_status(cur):
    """job_history status value is 'SUCCEED', not 'SUCCESS'."""
    run_sql(cur, """
        SELECT COUNT(*) FROM sys.information_schema.job_history
        WHERE status = 'SUCCEED'
          AND start_time >= CURRENT_DATE() - INTERVAL 1 DAY
    """)


def test_job_history_failed_status(cur):
    """FAILED status value is valid."""
    run_sql(cur, """
        SELECT COUNT(*) FROM sys.information_schema.job_history
        WHERE status = 'FAILED'
          AND start_time >= CURRENT_DATE() - INTERVAL 1 DAY
    """)


def test_job_history_success_wrong_value(cur):
    """'SUCCESS' is wrong status value — query should return 0 rows (not error, but wrong)."""
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM sys.information_schema.job_history
        WHERE status = 'SUCCESS'
          AND start_time >= CURRENT_DATE() - INTERVAL 7 DAY
    """)
    rows = cur.fetchall()
    cnt = rows[0][0] if rows else 0
    # This won't error but should return 0 — document the correct value
    assert cnt == 0, f"'SUCCESS' returned {cnt} rows — if non-zero, status enum has changed"


def test_show_jobs(cur):
    """SHOW JOBS must not error."""
    run_sql(cur, 'SHOW JOBS LIMIT 5')


def test_show_jobs_in_vcluster(cur):
    """SHOW JOBS IN VCLUSTER must not error."""
    run_sql(cur, 'SHOW JOBS IN VCLUSTER default_ap LIMIT 5')


def test_information_schema_columns(cur):
    """information_schema.columns query must work."""
    run_sql(cur, f"""
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = '{SCHEMA}'
        LIMIT 10
    """)


def test_information_schema_schemas(cur):
    """information_schema.schemas query must work."""
    run_sql(cur, 'SELECT * FROM information_schema.schemas LIMIT 5')
