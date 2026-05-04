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
| `test_index_manager.py` | clickzetta-index-manager | BLOOMFILTER/INVERTED/VECTOR INDEX CREATE, string column needs analyzer, BUILD/DROP/SHOW INDEX |
| `test_information_schema.py` | clickzetta-information-schema | `bytes` not `total_bytes`, pt_date partition, `SUCCEED` status, schemas/columns/users views |
| `test_zettapark.py` | clickzetta-zettapark | Session, filter/groupBy/.as_() (not .alias()), save_as_table, collect, to_pandas |
| `test_metadata_query.py` | clickzetta-metadata-query | SHOW TABLES/SCHEMAS/COLUMNS/VCLUSTERS/JOBS, DESC, FROM (SHOW) subquery, load_history() |
| `test_manage_comments.py` | clickzetta-manage-comments | ALTER TABLE SET COMMENT, CHANGE COLUMN COMMENT, COMMENT ON TABLE fails, quote escaping |
| `test_query_optimizer.py` | clickzetta-query-optimizer | EXPLAIN, EXPLAIN EXTENDED, SET result cache, ANALYZE TABLE, MAPJOIN hint |
| `test_vcluster_manager.py` | clickzetta-vcluster-manager | SHOW/DESC VCLUSTER, CREATE/ALTER/DROP VCLUSTER, USE VCLUSTER |
| `test_data_recovery.py` | clickzetta-data-recovery | DESC HISTORY, SHOW TABLES HISTORY, Time Travel, RESTORE, UNDROP, data_retention_days |
| `test_dba_guide.py` | clickzetta-dba-guide | CREATE/DROP USER/ROLE, GRANT/REVOKE, NETWORK POLICY COMMENT (no =), OPTIMIZE, ANALYZE |

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
