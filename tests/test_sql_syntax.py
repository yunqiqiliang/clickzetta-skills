"""
Validation tests for clickzetta-sql-syntax-guide skill.

Covers high-risk items from the migration traps table:
- NOW() is supported
- ARRAY_SIZE() is supported
- UNION / INTERSECT / EXCEPT are all supported
- DATEADD keyword unit (not string unit)
- ILIKE is supported
- QUALIFY is supported
- GROUP BY ALL
- named_struct vs STRUCT AS syntax
- COALESCE(x, 0) for ZEROIFNULL
- NULLIF(x, 0) for NULLIFZERO
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T = f'{SCHEMA}.syntax_test'


@pytest.fixture(scope='module', autouse=True)
def setup_table(cur):
    run_sql(cur, f"""
        CREATE TABLE IF NOT EXISTS {T} (
            id INT, name STRING, amount DOUBLE, dt DATE, tags ARRAY<STRING>
        )
    """)
    run_sql(cur, f"""
        INSERT INTO {T} VALUES
          (1, 'Alice', 100.0, DATE '2024-01-01', ARRAY('python', 'sql')),
          (2, 'Bob',   200.0, DATE '2024-01-02', ARRAY('java')),
          (3, 'alice', 150.0, DATE '2024-01-03', ARRAY())
    """)
    yield
    run_sql(cur, f'DROP TABLE IF EXISTS {T}')


def test_now_is_supported(cur):
    """NOW() must be supported."""
    cur.execute('SELECT NOW()')
    assert cur.fetchone() is not None


def test_current_timestamp_is_supported(cur):
    """CURRENT_TIMESTAMP() must be supported."""
    cur.execute('SELECT CURRENT_TIMESTAMP()')
    assert cur.fetchone() is not None


def test_array_size_is_supported(cur):
    """ARRAY_SIZE() is supported in ClickZetta (equivalent to SIZE(); both work)."""
    cur.execute(f'SELECT ARRAY_SIZE(tags) FROM {T} LIMIT 1')
    assert cur.fetchone() is not None


def test_size_is_supported(cur):
    """SIZE() must also be supported."""
    cur.execute(f'SELECT SIZE(tags) FROM {T} LIMIT 1')
    assert cur.fetchone() is not None


def test_union_all(cur):
    """UNION ALL must be supported."""
    run_sql(cur, f'SELECT id FROM {T} WHERE id = 1 UNION ALL SELECT id FROM {T} WHERE id = 2')


def test_union(cur):
    """UNION (dedup) must be supported."""
    run_sql(cur, f'SELECT id FROM {T} UNION SELECT id FROM {T}')


def test_intersect(cur):
    """INTERSECT must be supported."""
    run_sql(cur, f'SELECT id FROM {T} INTERSECT SELECT id FROM {T} WHERE id <= 2')


def test_except(cur):
    """EXCEPT must be supported."""
    run_sql(cur, f'SELECT id FROM {T} EXCEPT SELECT id FROM {T} WHERE id = 1')


def test_minus_is_supported(cur):
    """MINUS is supported as an alias for EXCEPT."""
    cur.execute(f'SELECT id FROM {T} MINUS SELECT id FROM {T} WHERE id = 1')
    rows = cur.fetchall()
    assert len(rows) == 2, f"MINUS should return 2 rows (id=2,3), got {rows}"


def test_dateadd_keyword_unit(cur):
    """DATEADD with keyword unit (day, not 'day') must work."""
    run_sql(cur, f"SELECT DATEADD(day, 7, dt) FROM {T} LIMIT 1")


def test_dateadd_string_unit_fails(cur):
    """DATEADD with string unit ('day') must fail — common migration trap."""
    run_sql(cur, "SELECT DATEADD('day', 7, CURRENT_DATE)", expect_error=True)


def test_ilike_is_supported(cur):
    """ILIKE (case-insensitive LIKE) must be supported."""
    cur.execute(f"SELECT * FROM {T} WHERE name ILIKE 'alice'")
    rows = cur.fetchall()
    assert len(rows) == 2, f"ILIKE should match both 'Alice' and 'alice', got {len(rows)}"


def test_qualify_is_supported(cur):
    """QUALIFY for window function filtering must be supported."""
    run_sql(cur, f"""
        SELECT id, name, amount,
               ROW_NUMBER() OVER (ORDER BY amount DESC) AS rn
        FROM {T}
        QUALIFY rn = 1
    """)


def test_group_by_all(cur):
    """GROUP BY ALL must be supported."""
    run_sql(cur, f'SELECT name, SUM(amount) FROM {T} GROUP BY ALL')


def test_named_struct(cur):
    """named_struct() must be supported."""
    run_sql(cur, f"SELECT named_struct('id', id, 'name', name) FROM {T} LIMIT 1")


def test_struct_as_syntax_fails(cur):
    """STRUCT(col AS alias) syntax must fail — use named_struct instead."""
    run_sql(cur, f"SELECT STRUCT(id AS my_id, name AS my_name) FROM {T} LIMIT 1",
            expect_error=True)


def test_coalesce_for_zeroifnull(cur):
    """COALESCE(x, 0) must work as ZEROIFNULL replacement."""
    run_sql(cur, f'SELECT COALESCE(amount, 0) FROM {T} LIMIT 1')


def test_nullif_for_nullifzero(cur):
    """NULLIF(x, 0) must work as NULLIFZERO replacement."""
    run_sql(cur, f'SELECT NULLIF(amount, 0) FROM {T} LIMIT 1')


def test_select_except(cur):
    """SELECT * EXCEPT(col) must be supported."""
    run_sql(cur, f'SELECT * EXCEPT(tags) FROM {T} LIMIT 1')


def test_lateral_view_explode(cur):
    """LATERAL VIEW EXPLODE must be supported."""
    run_sql(cur, f"""
        SELECT t.id, s.tag
        FROM {T} t
        LATERAL VIEW EXPLODE(t.tags) s AS tag
        LIMIT 5
    """)


# ---------------------------------------------------------------------------
# P1 cases: timestamp traps, CREATE OR REPLACE TABLE, WITH RECURSIVE,
# CREATE TEMPORARY TABLE
# ---------------------------------------------------------------------------

TS_SCHEMA = 'skill_test_ss2'
TS_TABLE = f'{TS_SCHEMA}.ts_test_syntax'


@pytest.fixture(scope='module')
def setup_ts_table(cur):
    """Create an isolated schema and TIMESTAMP table for P1 tests."""
    run_sql(cur, f'CREATE SCHEMA IF NOT EXISTS {TS_SCHEMA}')
    run_sql(cur, f'DROP TABLE IF EXISTS {TS_TABLE}')
    run_sql(cur, f'CREATE TABLE {TS_TABLE} (id INT, ts TIMESTAMP)')
    yield
    run_sql(cur, f'DROP TABLE IF EXISTS {TS_TABLE}')


def test_timestamp_string_insert_fails(cur, setup_ts_table):
    """Inserting a plain string into a TIMESTAMP column must fail.

    ClickZetta does not allow implicit cast from STRING to TIMESTAMP.
    Use CAST('...' AS TIMESTAMP) or the TIMESTAMP '...' literal instead.
    """
    run_sql(
        cur,
        f"INSERT INTO {TS_TABLE} VALUES (1, '2026-05-01 10:00:00')",
        expect_error=True,
    )


def test_timestamp_cast_insert(cur, setup_ts_table):
    """CAST('...' AS TIMESTAMP) must succeed when writing to a TIMESTAMP column."""
    run_sql(
        cur,
        f"INSERT INTO {TS_TABLE} VALUES (2, CAST('2026-05-01 10:00:00' AS TIMESTAMP))",
    )


def test_timestamp_literal_insert(cur, setup_ts_table):
    """TIMESTAMP '...' literal syntax must succeed when writing to a TIMESTAMP column."""
    run_sql(
        cur,
        f"INSERT INTO {TS_TABLE} VALUES (3, TIMESTAMP '2026-05-01 10:00:00')",
    )


def test_transaction_syntax_fails(cur):
    """BEGIN; COMMIT; transaction syntax is not supported."""
    run_sql(cur, "BEGIN; SELECT 1; COMMIT;", expect_error=True)


def test_charindex_fails_instr_works(cur):
    """CHARINDEX is not supported; INSTR is the replacement (note reversed arg order)."""
    run_sql(cur, "SELECT CHARINDEX('a', 'abc')", expect_error=True)
    cur.execute("SELECT INSTR('abc', 'a')")
    assert cur.fetchone() is not None


def test_lateral_flatten_fails(cur):
    """Snowflake LATERAL FLATTEN(input => arr) syntax is not supported."""
    run_sql(cur, f"""
        SELECT f.value FROM {T} t,
        LATERAL FLATTEN(input => t.tags) f
        LIMIT 1
    """, expect_error=True)


def test_bigint_identity(cur):
    """BIGINT IDENTITY auto-increment column must work."""
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SCHEMA}.identity_test (id BIGINT IDENTITY, val STRING)')
    run_sql(cur, f"INSERT INTO {SCHEMA}.identity_test (val) VALUES ('a'), ('b')")
    cur.execute(f'SELECT id, val FROM {SCHEMA}.identity_test ORDER BY id')
    rows = cur.fetchall()
    assert len(rows) >= 2
    ids = [r[0] for r in rows]
    assert ids == sorted(ids), "IDENTITY ids should be sequential"
    run_sql(cur, f'DROP TABLE IF EXISTS {SCHEMA}.identity_test')


def test_create_or_replace_table_succeeds(cur):
    """CREATE OR REPLACE TABLE is supported in ClickZetta (not a migration trap).

    Verified 2026-05-16: the statement executes without error.
    """
    run_sql(cur, f'DROP TABLE IF EXISTS {TS_SCHEMA}.replace_test')
    run_sql(cur, f'CREATE OR REPLACE TABLE {TS_SCHEMA}.replace_test (id INT, val STRING)')
    run_sql(cur, f'DROP TABLE IF EXISTS {TS_SCHEMA}.replace_test')


def test_with_recursive_fails(cur):
    """WITH RECURSIVE is not supported — syntax error at the CTE name."""
    run_sql(
        cur,
        'WITH RECURSIVE cte AS (SELECT 1 AS n UNION ALL SELECT n+1 FROM cte WHERE n < 5) SELECT * FROM cte',
        expect_error=True,
    )


def test_create_temporary_table_fails(cur):
    """CREATE TEMPORARY TABLE is not supported — raises 'not supported feature'."""
    run_sql(
        cur,
        f'CREATE TEMPORARY TABLE {TS_SCHEMA}.tmp_test (id INT)',
        expect_error=True,
    )
