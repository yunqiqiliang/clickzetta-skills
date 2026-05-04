"""
Shared connection fixture for skill validation tests.

Usage:
    python -m pytest tests/ -v
    python -m pytest tests/test_dynamic_table.py -v

Requires environment variables (or .env file in repo root):
    CLICKZETTA_SERVICE, CLICKZETTA_INSTANCE, CLICKZETTA_WORKSPACE,
    CLICKZETTA_USERNAME, CLICKZETTA_PASSWORD, CLICKZETTA_VCLUSTER
"""
import os
import pytest

# Load .env from repo root if present
_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_conn():
    import clickzetta.connector as cz
    return cz.connect(
        service=os.environ['CLICKZETTA_SERVICE'],
        instance=os.environ['CLICKZETTA_INSTANCE'],
        workspace=os.environ['CLICKZETTA_WORKSPACE'],
        username=os.environ['CLICKZETTA_USERNAME'],
        password=os.environ['CLICKZETTA_PASSWORD'],
        schema='skill_test',
        vcluster=os.environ.get('CLICKZETTA_VCLUSTER', 'default_ap'),
    )


@pytest.fixture(scope='session')
def conn():
    c = get_conn()
    cur = c.cursor()
    cur.execute('CREATE SCHEMA IF NOT EXISTS skill_test')
    yield c
    # cleanup schema after all tests
    try:
        cur.execute('DROP SCHEMA IF EXISTS skill_test CASCADE')
    except Exception:
        pass
    c.close()


@pytest.fixture(scope='session')
def cur(conn):
    return conn.cursor()


def run_sql(cursor, sql, expect_error=False):
    """Execute SQL and assert success or expected failure."""
    try:
        cursor.execute(sql)
        if expect_error:
            pytest.fail(f"Expected error but SQL succeeded:\n{sql}")
        return True
    except Exception as e:
        if expect_error:
            return str(e)
        pytest.fail(f"SQL failed unexpectedly:\n{sql}\nError: {e}")
