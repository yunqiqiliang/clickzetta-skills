# Skill Benchmark: clickzetta-sql-pipeline-manager

**Model**: claude-sonnet-4-6
**Date**: 2026-03-23
**Iteration**: 3

## Summary

| Metric | with_skill | without_skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 100.0% | 36.0% | +64.0% |

## Per-Eval Breakdown

| Eval | with_skill | without_skill | Key Difference |
|------|------------|---------------|----------------|
| 9. Kafka Full Pipeline | 7/7 | 3/7 | without_skill used EXTERNAL TABLE + TASK instead of CREATE PIPE + READ_KAFKA + DYNAMIC TABLE |
| 10. CDC Full Pipeline | 6/6 | 1/6 | without_skill used MERGE INTO + TASK, no Table Stream, no _change_type, no DYNAMIC TABLE |
| 11. OSS Full Pipeline | 6/6 | 1/6 | without_skill used EXTERNAL TABLE + TASK, wrong PIPE syntax, missing date in GROUP BY |
| 12. Medallion Architecture | 6/6 | 4/6 | without_skill used WAREHOUSE instead of VCLUSTER, bare COPY INTO instead of CREATE PIPE |

## Analyst Notes

- **Biggest gains**: Eval 10 (CDC, +83%) and Eval 11 (OSS, +83%) — without_skill completely missed ClickZetta-specific objects (Dynamic Table, Pipe), falling back to generic TASK-based scheduling
- **Eval 9 (Kafka)**: without_skill used EXTERNAL TABLE + KAFKA OPTIONS syntax — a plausible but wrong approach; skill correctly guides to READ_KAFKA inside CREATE PIPE
- **Eval 12 (Medallion)**: without_skill got the bronze/silver/gold naming right (it's a well-known pattern) but failed on VCLUSTER and CREATE PIPE syntax — exactly the ClickZetta-specific gaps the skill addresses
- **Pattern**: without_skill consistently falls back to TASK-based scheduling (CREATE TASK + SCHEDULE) for ETL pipelines — a generic SQL pattern that doesn't use ClickZetta's native Dynamic Table / Pipe objects
- **Iteration 2 vs 3**: Delta grew from +30% (evals 1-8) to +64% (evals 9-12) — the new pipeline wizard evals expose much larger gaps because they require end-to-end ClickZetta-specific knowledge
