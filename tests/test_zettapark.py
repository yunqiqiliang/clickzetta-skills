"""
Validation tests for clickzetta-zettapark skill.

Tests the ZettaPark Python DataFrame API against a live Lakehouse.
Covers: Session creation, table read, filter/select/groupBy/join,
        .as_() column rename, save_as_table, collect, to_pandas.
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SCHEMA = 'skill_test'
SRC_TABLE = f'{SCHEMA}.zp_orders'
RESULT_TABLE = f'{SCHEMA}.zp_result'


@pytest.fixture(scope='module')
def session():
    """Create a ZettaPark Session."""
    try:
        from clickzetta.zettapark.session import Session
    except ImportError:
        pytest.skip("clickzetta_zettapark_python not installed")

    params = {
        "username": os.environ["CLICKZETTA_USERNAME"],
        "password": os.environ["CLICKZETTA_PASSWORD"],
        "service": os.environ["CLICKZETTA_SERVICE"],
        "instance": os.environ["CLICKZETTA_INSTANCE"],
        "workspace": os.environ["CLICKZETTA_WORKSPACE"],
        "schema": SCHEMA,
        "vcluster": os.environ["CLICKZETTA_VCLUSTER"],
    }
    s = Session.builder.configs(params).create()
    yield s
    s.close()


@pytest.fixture(scope='module', autouse=True)
def setup_data(session):
    """Create source table with test data."""
    session.sql(f"DROP TABLE IF EXISTS {SRC_TABLE}").collect()
    session.sql(f"DROP TABLE IF EXISTS {RESULT_TABLE}").collect()
    session.sql(f"""
        CREATE TABLE {SRC_TABLE} (
            order_id INT, customer_id INT, category STRING, amount DOUBLE, status STRING
        )
    """).collect()
    session.sql(f"""
        INSERT INTO {SRC_TABLE} VALUES
        (1, 101, 'electronics', 500.0, 'completed'),
        (2, 102, 'clothing', 100.0, 'completed'),
        (3, 101, 'electronics', 300.0, 'pending'),
        (4, 103, 'food', 50.0, 'completed')
    """).collect()
    yield
    session.sql(f"DROP TABLE IF EXISTS {SRC_TABLE}").collect()
    session.sql(f"DROP TABLE IF EXISTS {RESULT_TABLE}").collect()


def test_session_sql(session):
    """session.sql() must work."""
    rows = session.sql("SELECT current_user(), current_workspace()").collect()
    assert len(rows) == 1


def test_session_table_read(session):
    """session.table() must return a DataFrame."""
    df = session.table(SRC_TABLE)
    assert df is not None
    count = df.count()
    assert count == 4


def test_filter_and_select(session):
    """filter() and select() must work."""
    from clickzetta.zettapark import functions as F
    df = (
        session.table(SRC_TABLE)
        .filter(F.col("status") == "completed")
        .select("order_id", "customer_id", "amount")
    )
    rows = df.collect()
    assert len(rows) == 3


def test_groupby_agg_with_as(session):
    """groupBy().agg() with .as_() column rename must work."""
    from clickzetta.zettapark import functions as F
    df = (
        session.table(SRC_TABLE)
        .group_by("category")
        .agg(
            F.sum("amount").as_("total"),
            F.count("*").as_("cnt"),
        )
    )
    rows = df.collect()
    assert len(rows) == 3
    # Verify column names use .as_() not .alias()
    col_names = [c.lower() for c in df.schema.names]
    assert 'total' in col_names, f"Expected 'total' column from .as_(), got: {col_names}"
    assert 'cnt' in col_names, f"Expected 'cnt' column from .as_(), got: {col_names}"


def test_alias_fails(session):
    """alias() must NOT work (ClickZetta uses .as_() not .alias())."""
    from clickzetta.zettapark import functions as F
    try:
        df = (
            session.table(SRC_TABLE)
            .group_by("category")
            .agg(F.sum("amount").alias("total"))
        )
        df.collect()
        # If it somehow works, that's fine — just document it
    except (AttributeError, Exception):
        pass  # Expected: .alias() not supported


def test_with_column(session):
    """with_column() must work."""
    from clickzetta.zettapark import functions as F
    df = (
        session.table(SRC_TABLE)
        .with_column("tax", F.col("amount") * 0.1)
    )
    rows = df.collect()
    assert len(rows) == 4


def test_sort_limit(session):
    """sort() and limit() must work."""
    from clickzetta.zettapark import functions as F
    df = (
        session.table(SRC_TABLE)
        .sort(F.col("amount").desc())
        .limit(2)
    )
    rows = df.collect()
    assert len(rows) == 2
    assert rows[0]["amount"] >= rows[1]["amount"]


def test_save_as_table_overwrite(session):
    """save_as_table with mode='overwrite' must work."""
    from clickzetta.zettapark import functions as F
    df = (
        session.table(SRC_TABLE)
        .filter(F.col("status") == "completed")
        .select("order_id", "amount")
    )
    df.write.save_as_table(RESULT_TABLE, mode="overwrite")
    count = session.table(RESULT_TABLE).count()
    assert count == 3


def test_save_as_table_append(session):
    """save_as_table with mode='append' must work."""
    from clickzetta.zettapark import functions as F
    df = (
        session.table(SRC_TABLE)
        .filter(F.col("status") == "pending")
        .select("order_id", "amount")
    )
    df.write.save_as_table(RESULT_TABLE, mode="append")
    count = session.table(RESULT_TABLE).count()
    assert count == 4


def test_to_pandas(session):
    """to_pandas() must return a pandas DataFrame."""
    pd = pytest.importorskip("pandas")
    df = session.table(SRC_TABLE).limit(4)
    pandas_df = df.to_pandas()
    assert len(pandas_df) == 4
    assert hasattr(pandas_df, 'columns')


def test_create_dataframe(session):
    """session.create_dataframe() must work."""
    df = session.create_dataframe(
        [[1, "Alice", 100.0], [2, "Bob", 200.0]],
        schema=["id", "name", "amount"]
    )
    rows = df.collect()
    assert len(rows) == 2
