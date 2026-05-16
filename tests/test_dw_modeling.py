"""
Validation tests for clickzetta-dw-modeling skill.

Covers the DDL patterns recommended by the skill:
- CREATE TABLE with PARTITIONED BY (days(col)) — ClickZetta syntax
- CREATE TABLE with CLUSTERED BY ... INTO N BUCKETS
- CREATE TABLE with PROPERTIES (data_retention_days)
- CREATE DYNAMIC TABLE with REFRESH interval VCLUSTER (DWS/Gold layer)
- PARTITIONED BY (col) without days() must fail (wrong syntax)
- information_schema.tables query with bytes/row_count
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T_ODS = f'{SCHEMA}.dw_ods_orders'
T_DWD = f'{SCHEMA}.dw_dwd_orders'
T_DWS = f'{SCHEMA}.dw_dws_summary'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    for t in [T_DWS, T_DWD, T_ODS]:
        try:
            cur.execute(f'DROP DYNAMIC TABLE IF EXISTS {t}')
        except Exception:
            pass
        try:
            cur.execute(f'DROP TABLE IF EXISTS {t}')
        except Exception:
            pass
    yield
    for t in [T_DWS, T_DWD, T_ODS]:
        try:
            cur.execute(f'DROP DYNAMIC TABLE IF EXISTS {t}')
        except Exception:
            pass
        try:
            cur.execute(f'DROP TABLE IF EXISTS {t}')
        except Exception:
            pass


def test_create_table_partitioned_by_days(cur):
    """CREATE TABLE PARTITIONED BY (days(col)) must work."""
    run_sql(cur, f"""
        CREATE TABLE IF NOT EXISTS {T_ODS} (
            order_id   BIGINT,
            user_id    BIGINT,
            amount     DECIMAL(18, 2),
            status     STRING,
            created_at TIMESTAMP,
            _op        STRING,
            _ts        TIMESTAMP
        )
        PARTITIONED BY (days(created_at))
        COMMENT 'ODS 订单原始表'
    """)


def test_create_table_clustered_by_buckets(cur):
    """CREATE TABLE CLUSTERED BY ... INTO N BUCKETS must work."""
    run_sql(cur, f"""
        CREATE TABLE IF NOT EXISTS {T_DWD} (
            order_id   BIGINT,
            user_id    BIGINT,
            amount     DECIMAL(18, 2),
            status     STRING,
            order_date DATE
        )
        PARTITIONED BY (days(order_date))
        CLUSTERED BY (user_id) INTO 8 BUCKETS
        COMMENT 'DWD 订单事实表'
    """)


def test_create_table_partitioned_by_col_succeeds(cur):
    """PARTITIONED BY (col) without days() now succeeds.

    Verified 2026-05-16: ClickZetta now allows plain column partitioning
    without the days() transform (behavior changed from earlier versions).
    """
    run_sql(cur, f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.dw_plain_partition (
            id INT, dt DATE
        )
        PARTITIONED BY (dt)
    """)
    try:
        cur.execute(f'DROP TABLE IF EXISTS {SCHEMA}.dw_plain_partition')
    except Exception:
        pass


def test_create_table_with_data_retention(cur):
    """CREATE TABLE with data_retention_days PROPERTIES must work."""
    run_sql(cur, f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.dw_retention_test (
            id INT, val STRING
        )
        PROPERTIES ('data_retention_days'='7')
    """)
    try:
        cur.execute(f'DROP TABLE IF EXISTS {SCHEMA}.dw_retention_test')
    except Exception:
        pass


def test_insert_into_partitioned_table(cur):
    """INSERT INTO partitioned table must work."""
    run_sql(cur, f"""
        INSERT INTO {T_ODS} (order_id, user_id, amount, status, created_at, _op, _ts)
        VALUES (1, 101, 100.0, 'completed',
                CAST('2024-01-01 10:00:00' AS TIMESTAMP),
                'I',
                CAST('2024-01-01 10:00:00' AS TIMESTAMP))
    """)


def test_create_dynamic_table_dws_layer(cur):
    """CREATE DYNAMIC TABLE for DWS/Gold layer must work."""
    run_sql(cur, f"""
        CREATE OR REPLACE DYNAMIC TABLE {T_DWS}
          REFRESH interval 1 HOUR
          VCLUSTER default_ap
        AS
        SELECT
            user_id,
            DATE(created_at) AS order_date,
            COUNT(order_id) AS order_cnt,
            SUM(amount) AS total_amount
        FROM {T_ODS}
        WHERE _op != 'D'
        GROUP BY user_id, DATE(created_at)
    """)


def test_information_schema_tables_query(cur):
    """information_schema.tables query with bytes/row_count must work."""
    cur.execute(f"""
        SELECT table_schema, table_name, table_type,
               ROUND(bytes/1024.0/1024/1024, 2) AS size_gb,
               row_count
        FROM information_schema.tables
        WHERE table_type = 'MANAGED_TABLE'
          AND table_schema = '{SCHEMA}'
        ORDER BY bytes DESC NULLS LAST
        LIMIT 10
    """)
    col_names = [d[0].lower() for d in cur.description]
    assert 'size_gb' in col_names  # bytes is aliased as size_gb via ROUND(...) AS size_gb
    assert 'row_count' in col_names


def test_refresh_dynamic_table_after_create(cur):
    """REFRESH DYNAMIC TABLE command must be syntactically valid.

    If the dynamic table feature is unavailable in this environment the test
    is skipped.  When available, REFRESH must succeed after CREATE.
    """
    import pytest as _pytest
    # T_DWS may not exist if DT feature is unavailable; skip gracefully
    try:
        cur.execute(f'REFRESH DYNAMIC TABLE {T_DWS}')
    except Exception as e:
        err = str(e)
        if 'not available' in err.lower() or 'dynamic_table not found' in err.lower():
            _pytest.skip(f"Dynamic table feature not available: {err[:80]}")
        raise


def test_left_join_where_clause_trap(cur):
    """LEFT JOIN + WHERE on right-table column degrades to INNER JOIN."""
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SCHEMA}.dw_left_a (id INT, val STRING)')
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SCHEMA}.dw_left_b (id INT, extra STRING)')
    run_sql(cur, f"INSERT INTO {SCHEMA}.dw_left_a VALUES (1,'a'),(2,'b'),(3,'c')")
    run_sql(cur, f"INSERT INTO {SCHEMA}.dw_left_b VALUES (1,'x')")

    cur.execute(f"""
        SELECT a.id FROM {SCHEMA}.dw_left_a a
        LEFT JOIN {SCHEMA}.dw_left_b b ON a.id = b.id
    """)
    full_rows = len(cur.fetchall())

    cur.execute(f"""
        SELECT a.id FROM {SCHEMA}.dw_left_a a
        LEFT JOIN {SCHEMA}.dw_left_b b ON a.id = b.id
        WHERE b.extra = 'x'
    """)
    filtered_rows = len(cur.fetchall())

    assert full_rows == 3, f"LEFT JOIN without WHERE should return 3 rows, got {full_rows}"
    assert filtered_rows == 1, f"LEFT JOIN + WHERE degrades to INNER JOIN, expected 1 row, got {filtered_rows}"

    run_sql(cur, f'DROP TABLE IF EXISTS {SCHEMA}.dw_left_a')
    run_sql(cur, f'DROP TABLE IF EXISTS {SCHEMA}.dw_left_b')


def test_information_schema_tables_last_modify_time(cur):
    """information_schema.tables must have last_modify_time column."""
    cur.execute(f"""
        SELECT table_schema, table_name, last_modify_time
        FROM information_schema.tables
        WHERE table_schema = '{SCHEMA}'
        LIMIT 3
    """)
    col_names = [d[0].lower() for d in cur.description]
    assert 'last_modify_time' in col_names
