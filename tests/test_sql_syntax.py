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
    """ARRAY_SIZE() must be supported (not just SIZE())."""
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
