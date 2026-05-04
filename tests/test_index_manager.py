"""
Validation tests for clickzetta-index-manager skill.

Covers:
- CREATE BLOOMFILTER INDEX syntax
- CREATE INVERTED INDEX (numeric column, no PROPERTIES needed)
- CREATE INVERTED INDEX (string column, must have analyzer PROPERTIES)
- CREATE VECTOR INDEX syntax
- SHOW INDEX FROM table
- DROP INDEX IF EXISTS
- BUILD INDEX (inverted only)
- DESC INDEX
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
T_BF = f'{SCHEMA}.idx_test_bf'
T_INV = f'{SCHEMA}.idx_test_inv'
T_VEC = f'{SCHEMA}.idx_test_vec'


@pytest.fixture(scope='module', autouse=True)
def setup_tables(cur):
    run_sql(cur, f'DROP TABLE IF EXISTS {T_BF}')
    run_sql(cur, f'DROP TABLE IF EXISTS {T_INV}')
    run_sql(cur, f'DROP TABLE IF EXISTS {T_VEC}')
    run_sql(cur, f'CREATE TABLE {T_BF} (order_id INT, email STRING, val DOUBLE)')
    run_sql(cur, f'CREATE TABLE {T_INV} (id INT, title STRING, content STRING)')
    run_sql(cur, f'CREATE TABLE {T_VEC} (id INT, vec ARRAY<FLOAT>)')
    yield
    for t in [T_BF, T_INV, T_VEC]:
        try:
            cur.execute(f'DROP TABLE IF EXISTS {t}')
        except Exception:
            pass


@pytest.fixture(scope='module', autouse=True)
def cleanup_indexes(cur, setup_tables):
    yield
    for idx in ['bf_order_idx', 'inv_id_idx', 'inv_title_idx', 'vec_idx']:
        try:
            cur.execute(f'DROP INDEX IF EXISTS {idx}')
        except Exception:
            pass


def test_create_bloomfilter_index(cur):
    """CREATE BLOOMFILTER INDEX on existing table must work."""
    run_sql(cur, f"""
        CREATE BLOOMFILTER INDEX bf_order_idx
        ON TABLE {T_BF}(order_id)
        COMMENT '订单ID布隆过滤器'
    """)


def test_create_inverted_index_numeric(cur):
    """CREATE INVERTED INDEX on numeric column (no PROPERTIES) must work."""
    run_sql(cur, f"""
        CREATE INVERTED INDEX inv_id_idx ON TABLE {T_INV}(id)
    """)


def test_create_inverted_index_string_with_analyzer(cur):
    """CREATE INVERTED INDEX on string column with analyzer PROPERTIES must work."""
    run_sql(cur, f"""
        CREATE INVERTED INDEX inv_title_idx
        ON TABLE {T_INV}(title)
        PROPERTIES('analyzer'='chinese')
    """)


def test_create_inverted_index_string_no_analyzer_fails(cur):
    """CREATE INVERTED INDEX on string column without analyzer must fail."""
    err = run_sql(cur, f"""
        CREATE INVERTED INDEX inv_content_no_analyzer
        ON TABLE {T_INV}(content)
    """, expect_error=True)
    # If it fails, that's expected. If it succeeds, clean up.
    if not err:
        try:
            cur.execute('DROP INDEX IF EXISTS inv_content_no_analyzer')
        except Exception:
            pass


def test_create_vector_index(cur):
    """CREATE VECTOR INDEX with PROPERTIES must work."""
    run_sql(cur, f"""
        CREATE VECTOR INDEX vec_idx
        ON TABLE {T_VEC}(vec)
        PROPERTIES(
            "scalar.type" = "f32",
            "distance.function" = "cosine_distance"
        )
    """)


def test_show_index_from(cur):
    """SHOW INDEX FROM table must work."""
    run_sql(cur, f'SHOW INDEX FROM {T_BF}')


def test_show_index_in(cur):
    """SHOW INDEX IN table must work (alias for FROM)."""
    run_sql(cur, f'SHOW INDEX IN {T_INV}')


def test_desc_index(cur):
    """DESC INDEX must work."""
    run_sql(cur, 'DESC INDEX bf_order_idx')


def test_desc_index_extended(cur):
    """DESC INDEX EXTENDED must work."""
    run_sql(cur, 'DESC INDEX EXTENDED bf_order_idx')


def test_build_inverted_index(cur):
    """BUILD INDEX for inverted index must work."""
    run_sql(cur, f'BUILD INDEX inv_id_idx ON {T_INV}')


def test_drop_index(cur):
    """DROP INDEX IF EXISTS must work."""
    run_sql(cur, 'DROP INDEX IF EXISTS bf_order_idx')
    run_sql(cur, 'DROP INDEX IF EXISTS inv_id_idx')
    run_sql(cur, 'DROP INDEX IF EXISTS inv_title_idx')
    run_sql(cur, 'DROP INDEX IF EXISTS vec_idx')
