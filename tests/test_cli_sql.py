"""
cz-cli validation tests for SQL-based skills.

Covers cz-cli commands from:
- clickzetta-monitoring: cz-cli sql "SHOW JOBS ..." --sync
- clickzetta-metadata:   cz-cli sql "SHOW TABLES/SCHEMAS/..." --sync
- clickzetta-table-lineage: cz-cli sql -f <file> --sync, cz-cli sql --no-limit

Skills tested: clickzetta-monitoring, clickzetta-metadata, clickzetta-table-lineage
"""
import json
import subprocess
import tempfile
import os
import pytest

CLI_PROFILE = "skill_test"


def cz_sql(sql: str, extra_args: list[str] = None) -> dict:
    """Run cz-cli sql --sync and return parsed JSON."""
    cmd = ["cz-cli", "--profile", CLI_PROFILE, "sql", "--sync", sql]
    if extra_args:
        cmd += extra_args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout.strip() or result.stderr.strip())


# ---------------------------------------------------------------------------
# clickzetta-monitoring
# ---------------------------------------------------------------------------

def test_show_jobs_limit():
    """cz-cli sql 'SHOW JOBS LIMIT 20' --sync must return jobs data."""
    d = cz_sql("SHOW JOBS LIMIT 20")
    assert "error" not in d, f"Unexpected error: {d.get('error')}"
    assert "columns" in d
    assert "rows" in d
    assert "job_id" in d["columns"]


def test_show_jobs_table_output():
    """cz-cli sql 'SHOW JOBS LIMIT 5' --sync -o table must not error."""
    cmd = ["cz-cli", "--profile", CLI_PROFILE, "sql", "--sync", "SHOW JOBS LIMIT 5", "-o", "table"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    assert len(result.stdout.strip()) > 0


def test_job_history_query():
    """cz-cli sql on sys.information_schema.job_history must return columns/rows."""
    d = cz_sql(
        "SELECT * FROM sys.information_schema.job_history "
        "WHERE pt_date >= CAST(CURRENT_DATE() - INTERVAL 1 DAY AS DATE) LIMIT 10"
    )
    assert "error" not in d, f"Unexpected error: {d.get('error')}"
    assert "columns" in d
    assert "rows" in d


# ---------------------------------------------------------------------------
# clickzetta-metadata
# ---------------------------------------------------------------------------

def test_show_tables_in_schema():
    """cz-cli sql 'SHOW TABLES IN public' --sync must return table list."""
    d = cz_sql("SHOW TABLES IN public")
    assert "error" not in d, f"Unexpected error: {d.get('error')}"
    assert "columns" in d
    assert "rows" in d


def test_show_schemas():
    """cz-cli sql 'SHOW SCHEMAS' --sync must return schema list."""
    d = cz_sql("SHOW SCHEMAS")
    assert "error" not in d, f"Unexpected error: {d.get('error')}"
    assert "columns" in d
    assert "rows" in d
    assert len(d["rows"]) > 0


def test_information_schema_tables():
    """cz-cli sql on information_schema.tables must return rows."""
    d = cz_sql("SELECT * FROM information_schema.tables LIMIT 10")
    assert "error" not in d, f"Unexpected error: {d.get('error')}"
    assert "columns" in d
    assert "rows" in d


@pytest.fixture(scope="module", autouse=True)
def ensure_schema():
    """Ensure skill_test schema and anchor table exist for CLI tests."""
    subprocess.run(
        ["cz-cli", "--profile", CLI_PROFILE, "sql", "--sync", "--write",
         "CREATE SCHEMA IF NOT EXISTS skill_test"],
        capture_output=True
    )
    subprocess.run(
        ["cz-cli", "--profile", CLI_PROFILE, "sql", "--sync", "--write",
         "CREATE TABLE IF NOT EXISTS skill_test.cli_test_anchor (id INT)"],
        capture_output=True
    )
    yield
    subprocess.run(
        ["cz-cli", "--profile", CLI_PROFILE, "sql", "--sync", "--write",
         "DROP TABLE IF EXISTS skill_test.cli_test_anchor"],
        capture_output=True
    )


def test_load_history_function():
    """cz-cli sql load_history() syntax must be valid (returns empty rows if no COPY jobs)."""
    d = cz_sql("SELECT * FROM load_history('skill_test.cli_test_anchor') LIMIT 20")
    assert "error" not in d, f"Unexpected error: {d.get('error')}"
    assert "columns" in d


def test_show_connections():
    """cz-cli sql 'SHOW CONNECTIONS' --sync must return connection list."""
    d = cz_sql("SHOW CONNECTIONS")
    assert "error" not in d, f"Unexpected error: {d.get('error')}"
    assert "columns" in d


def test_show_vclusters():
    """cz-cli sql 'SHOW VCLUSTERS' --sync must return vcluster list."""
    d = cz_sql("SHOW VCLUSTERS")
    assert "error" not in d, f"Unexpected error: {d.get('error')}"
    assert "columns" in d
    assert len(d["rows"]) > 0


# ---------------------------------------------------------------------------
# clickzetta-table-lineage: cz-cli sql -f <file>
# ---------------------------------------------------------------------------

def test_sql_from_file():
    """cz-cli sql -f <file> --sync must execute SQL from a file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write("SELECT 1 AS lineage_test")
        fpath = f.name
    try:
        cmd = ["cz-cli", "--profile", CLI_PROFILE, "sql", "--sync", "-f", fpath]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        d = json.loads(result.stdout.strip())
        assert "error" not in d
        assert d["rows"][0]["lineage_test"] == 1
    finally:
        os.unlink(fpath)


def test_sql_no_limit_flag():
    """cz-cli sql --no-limit --sync must execute without row limit."""
    cmd = ["cz-cli", "--profile", CLI_PROFILE, "sql", "--sync",
           "--no-limit", "SELECT 1 AS ok"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    d = json.loads(result.stdout.strip())
    assert "error" not in d
    assert d["rows"][0]["ok"] == 1
