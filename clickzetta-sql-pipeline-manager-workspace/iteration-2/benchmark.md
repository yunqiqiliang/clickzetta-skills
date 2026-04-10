# Skill Benchmark: clickzetta-sql-pipeline-manager

**Model**: claude-sonnet-4-6
**Date**: 2026-03-23
**Iteration**: 2

## Summary

| Metric | with_skill | without_skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 100.0% | 70.0% | +30.0% |

## Per-Eval Breakdown

| Eval | with_skill | without_skill | Key Difference |
|------|------------|---------------|----------------|
| 1. Create Dynamic Table | 6/6 | 5/6 | without_skill used COMPUTE_CLUSTER instead of VCLUSTER |
| 2. Troubleshoot Refresh | 4/4 | 3/4 | without_skill used INFORMATION_SCHEMA instead of SHOW DYNAMIC TABLE REFRESH HISTORY |
| 3. Kafka Pipe | 6/6 | 3/6 | without_skill used wrong Kafka syntax (not READ_KAFKA) |
| 4. CDC Stream | 6/6 | 2/6 | without_skill used Snowflake METADATA$ACTION instead of _change_type |
| 5. Materialized View | 6/6 | 5/6 | without_skill used REFRESH EVERY 1 HOUR instead of REFRESH AUTO EVERY '1 hours' |
| 6. Multi-layer ETL | 5/5 | 5/5 | Both passed (DOWNSTREAM concept is well-known) |
| 7. Suspend/Resume | 3/3 | 2/3 | without_skill used SHOW DYNAMIC TABLES instead of SHOW TABLES WHERE is_dynamic=true |
| 8. DT vs MV | 4/4 | 3/4 | without_skill lacked ClickZetta-specific REFRESH syntax |

## Analyst Notes

- **Biggest gains**: Eval 3 (Kafka Pipe, +50%) and Eval 4 (CDC Stream, +67%) — these involve the most ClickZetta-specific syntax
- **No gain**: Eval 6 (Multi-layer ETL) — DOWNSTREAM concept is general enough that Claude knows it without the skill
- **Iteration 1 vs 2**: Pass rate improved from 90.6% → 100% (with_skill) and 90.6% → 70% (without_skill), meaning the delta grew from +9.4% to +30%
- The skill now clearly differentiates on ClickZetta-specific syntax: VCLUSTER, READ_KAFKA, REFRESH AUTO EVERY, _change_type
