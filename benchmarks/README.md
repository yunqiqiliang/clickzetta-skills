# cz-cli Benchmark: Direct Commands vs Agent Run

Measures wall-clock time, tool call chains, and multi-turn context transfer
accuracy between two cz-cli invocation strategies.

## Quick start

```bash
pip install -r requirements.txt

# Run all cases (3 runs each, ~30 min)
python runner.py --profile <your-profile> --runs 3

# Run only multi-turn cases
python runner.py --profile <your-profile> --type multi --runs 1

# Run a single case
python runner.py --case Q1 --runs 1

# Generate HTML report
python report.py results/<run-id>/summary.json
```

## Test cases

| ID | Type | Scenario |
|----|------|---------|
| Q1 | single | Query failed jobs (monitoring) |
| Q2 | single | Diagnose slow JOIN query |
| Q3 | single | Check dynamic table refresh history |
| O1 | single | Create dynamic table |
| O2 | single | Create offline sync task |
| M1 | multi | Inspect table → build sync task |
| M2 | multi | Find slowest job → optimize SQL |
| M3 | multi | Create DT → check status → change interval |

## Metrics

- **total_time_ms**: wall-clock time per approach (primary metric)
- **tool_call_count**: number of tool invocations
- **tool_sequence**: ordered list of tool names called
- **context_transfer_score**: fraction of expected key values present in follow-up output (multi-turn only, 0.0–1.0)

## Output

Results are saved to `results/<run-id>/` as JSON files. Generate an HTML report with three views:
1. Summary table — median time and tool call counts per case
2. Timeline bars — visual comparison of execution time
3. Context transfer heatmap — multi-turn cases only
