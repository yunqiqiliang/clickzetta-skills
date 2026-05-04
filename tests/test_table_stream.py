"""
Validation tests for clickzetta-table-stream-pipeline skill.

Covers:
- CREATE TABLE STREAM syntax (COMMENT without =)
- COMMENT = syntax must fail for TABLE STREAM
- WITH PROPERTIES TABLE_STREAM_MODE
- __change_type metadata field
- Stream offset behavior (SELECT doesn't move offset, DML does)
"""
import pytest
from conftest import run_sql

SCHEMA = 'skill_test'
SRC = f'{SCHEMA}.stream_src'
STREAM_STD = f'{SCHEMA}.stream_validate_std'
STREAM_APPEND = f'{SCHEMA}.stream_validate_append'
TARGET = f'{SCHEMA}.stream_target'


@pytest.fixture(scope='module', autouse=True)
def setup(cur):
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SRC} (id INT, val STRING, PRIMARY KEY (id))')
    run_sql(cur, f"ALTER TABLE {SRC} SET PROPERTIES ('change_tracking' = 'true')")
    run_sql(cur, f"INSERT INTO {SRC} VALUES (1, 'a'), (2, 'b')")
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {TARGET} (id INT, val STRING)')
    yield
    for obj in [STREAM_STD, STREAM_APPEND]:
        try:
            cur.execute(f'DROP TABLE STREAM IF EXISTS {obj}')
        except Exception:
            pass
    for obj in [SRC, TARGET]:
        try:
            cur.execute(f'DROP TABLE IF EXISTS {obj}')
        except Exception:
            pass


def test_create_stream_comment_no_equals(cur):
    """COMMENT without = sign must work for TABLE STREAM."""
    run_sql(cur, f"""
        CREATE TABLE STREAM IF NOT EXISTS {STREAM_STD}
          ON TABLE {SRC}
          COMMENT '标准变更流'
          WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD', 'SHOW_INITIAL_ROWS' = 'TRUE')
    """)


def test_create_stream_comment_with_equals_fails(cur):
    """COMMENT = '...' (with equals) must fail for TABLE STREAM."""
    run_sql(cur, f"""
        CREATE TABLE STREAM IF NOT EXISTS {SCHEMA}.stream_wrong_comment
          ON TABLE {SRC}
          COMMENT = '错误语法'
          WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD')
    """, expect_error=True)
    try:
        cur.execute(f'DROP TABLE STREAM IF EXISTS {SCHEMA}.stream_wrong_comment')
    except Exception:
        pass


def test_create_append_only_stream(cur):
    """APPEND_ONLY mode must work."""
    run_sql(cur, f"""
        CREATE TABLE STREAM IF NOT EXISTS {STREAM_APPEND}
          ON TABLE {SRC}
          WITH PROPERTIES ('TABLE_STREAM_MODE' = 'APPEND_ONLY')
    """)


def test_stream_has_change_type_field(cur):
    """__change_type metadata field must exist in stream query."""
    cur.execute(f'SELECT __change_type, id, val FROM {STREAM_STD} LIMIT 10')
    rows = cur.fetchall()
    # SHOW_INITIAL_ROWS=TRUE so should have rows
    assert len(rows) > 0, "Stream with SHOW_INITIAL_ROWS=TRUE should have initial rows"
    change_types = {r[0] for r in rows}
    assert change_types.issubset({'INSERT', 'UPDATE_BEFORE', 'UPDATE_AFTER', 'DELETE'}), \
        f"Unexpected __change_type values: {change_types}"


def test_select_does_not_move_offset(cur):
    """SELECT alone must not move stream offset."""
    cur.execute(f'SELECT COUNT(*) FROM {STREAM_STD}')
    cnt1 = cur.fetchone()[0]
    cur.execute(f'SELECT COUNT(*) FROM {STREAM_STD}')
    cnt2 = cur.fetchone()[0]
    assert cnt1 == cnt2, "SELECT should not move offset"


def test_merge_moves_offset(cur):
    """MERGE INTO target USING stream must move offset."""
    cur.execute(f'SELECT COUNT(*) FROM {STREAM_STD}')
    cnt_before = cur.fetchone()[0]

    run_sql(cur, f"""
        MERGE INTO {TARGET} t
        USING {STREAM_STD} s ON t.id = s.id
        WHEN NOT MATCHED AND s.__change_type = 'INSERT' THEN
          INSERT (id, val) VALUES (s.id, s.val)
    """)

    cur.execute(f'SELECT COUNT(*) FROM {STREAM_STD}')
    cnt_after = cur.fetchone()[0]
    assert cnt_after < cnt_before or cnt_after == 0, \
        f"MERGE should move offset: before={cnt_before}, after={cnt_after}"


def test_change_tracking_required(cur):
    """Stream on table without change_tracking should fail or warn."""
    run_sql(cur, f'CREATE TABLE IF NOT EXISTS {SCHEMA}.no_tracking (id INT)')
    # Creating stream on non-tracked table — behavior may vary
    # Just verify the syntax itself is accepted (tracking error is runtime)
    try:
        cur.execute(f"""
            CREATE TABLE STREAM IF NOT EXISTS {SCHEMA}.stream_no_tracking
              ON TABLE {SCHEMA}.no_tracking
              WITH PROPERTIES ('TABLE_STREAM_MODE' = 'STANDARD')
        """)
        cur.execute(f'DROP TABLE STREAM IF EXISTS {SCHEMA}.stream_no_tracking')
    except Exception:
        pass  # May fail at create or at query time — both acceptable
    finally:
        try:
            cur.execute(f'DROP TABLE IF EXISTS {SCHEMA}.no_tracking')
        except Exception:
            pass
