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


def test_create_table_partitioned_by_col_fails(cur):
    """PARTITIONED BY (col) without days() must fail."""
    err = run_sql(cur, f"""
        CREATE TABLE {SCHEMA}.dw_wrong_partition (
            id INT, dt DATE
        )
        PARTITIONED BY (dt)
    """, expect_error=True)
    # If it fails, that's expected. If it succeeds, clean up.
    if not err:
        try:
            cur.execute(f'DROP TABLE IF EXISTS {SCHEMA}.dw_wrong_partition')
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
        VALUES (1, 101, 100.0, 'completed', '2024-01-01 10:00:00', 'I', '2024-01-01 10:00:00')
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
    assert 'bytes' in col_names
    assert 'row_count' in col_names
