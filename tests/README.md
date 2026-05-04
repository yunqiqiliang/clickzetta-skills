# Skill Validation Tests

Live integration tests that verify every SQL example in the skills actually works against a real ClickZetta Lakehouse environment.

## Setup

```bash
pip install clickzetta-connector pytest
```

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

## Running Tests

```bash
# Run all tests
cd tests/
python -m pytest . -v

# Run a specific skill
python -m pytest test_dynamic_table.py -v
python -m pytest test_sql_syntax.py -v

# Run with short output
python -m pytest . -q
```

## Test Files

| File | Skill | Key Assertions |
|---|---|---|
| `test_dynamic_table.py` | clickzetta-dynamic-table | PROPERTIES syntax, REFRESH interval syntax, SUSPEND/RESUME, SHOW TABLES WHERE is_dynamic |
| `test_monitoring.py` | clickzetta-monitoring | `bytes` not `total_bytes`, `SUCCEED` not `SUCCESS`, SHOW JOBS |
| `test_sql_syntax.py` | clickzetta-sql-syntax-guide | NOW(), ARRAY_SIZE(), UNION/INTERSECT/EXCEPT, DATEADD keyword unit, ILIKE, QUALIFY |
| `test_table_stream.py` | clickzetta-table-stream-pipeline | COMMENT without =, __change_type field, offset behavior |
| `test_access_control.py` | clickzetta-access-control | SHOW NETWORK POLICY (singular), GRANT/REVOKE, CREATE ROLE |
| `test_data_lifecycle.py` | clickzetta-data-lifecycle | DESC HISTORY columns, Time Travel, UNDROP, RESTORE |

## Environment Variables

| Variable | Example | Description |
|---|---|---|
| `CLICKZETTA_SERVICE` | `cn-shanghai-alicloud.api.clickzetta.com` | Service endpoint |
| `CLICKZETTA_INSTANCE` | `f8866243` | Instance ID |
| `CLICKZETTA_WORKSPACE` | `quick_start` | Workspace name |
| `CLICKZETTA_USERNAME` | `admin` | Username |
| `CLICKZETTA_PASSWORD` | `***` | Password |
| `CLICKZETTA_VCLUSTER` | `default_ap` | VCluster name |

## Design Principles

1. **Isolated schema**: All tests run in `skill_test` schema, cleaned up after the session.
2. **Negative tests**: Wrong syntax is explicitly tested to fail (`expect_error=True`), not just omitted.
3. **Authoritative**: A passing test means the skill's SQL is correct. A failing test means the skill needs a fix.
4. **No mocks**: Tests hit the real Lakehouse — no mocking, no stubs.
