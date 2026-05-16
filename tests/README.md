# ClickZetta Skill Validation Tests

This directory contains the test framework for the `clickzetta-*` skills.

The framework has two complementary goals:

1. Verify ClickZetta product facts with real Lakehouse execution.
2. Evaluate the skills themselves as AI-agent artifacts: structure, trigger quality, value uplift, and skill-boundary overlap.

In other words, the tests check both "is the ClickZetta guidance correct?" and "does the agent actually use the right skill at the right time?"

## Architecture

The current framework has six layers:

| Layer | Entry Point | Purpose |
|---|---|---|
| Static contract checks | `test_static_skill_contract.py` | Validate `SKILL.md`, `.well-known/skills/index.json`, and `eval_cases.jsonl` structure |
| Trigger eval | `skill_eval/trigger_eval.py` | Measure whether `should_call` / `should_not_call` cases trigger the right skill |
| A/B uplift eval | `skill_eval/ab_eval.py` | Compare `with_skill` vs `baseline` outputs to measure whether a skill actually helps |
| Agent-orchestrated eval | `agent_eval/RUNBOOK.md` | Let Claude/Codex run evals with parallel workers and emit structured JSONL |
| Overlap analysis | `skill_eval/overlap.py` | Detect possible skill confusion or duplicated scope using description/case similarity |
| Live Lakehouse tests | `test_*.py` | Execute real SQL against ClickZetta Lakehouse to verify syntax and runtime behavior |

The reporting layer in `skill_eval/report.py` aggregates static validation, script-driven trigger eval, script-driven A/B eval, agent-orchestrated eval, and overlap analysis into both Markdown and HTML reports.

## Setup

```bash
pip install -r tests/requirements.txt
```

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

## Running Tests

Run from the repository root unless noted otherwise.

```bash
# Run all pytest tests, including static contract checks and live Lakehouse tests
python -m pytest tests/ -v

# Run only static skill contract checks
python -m pytest tests/test_static_skill_contract.py -q

# Run a specific live product test
python -m pytest tests/test_dynamic_table.py -v
python -m pytest tests/test_sql_syntax.py -v

# Run with short output
python -m pytest tests/ -q
```

## Skill Framework Evaluation

The `tests/skill_eval` package evaluates skills as reusable AI-agent capabilities.

### Static validation and report only

This command does not require an agent command or Lakehouse credentials. It validates repository structure and generates overlap analysis.

```bash
python -m tests.skill_eval.run_all --root . --report-root reports
```

Generated report layout:

```text
reports/skill-eval-YYYYMMDD-HHMMSS/
  raw/
    static_results.json
    trigger_results.jsonl        # present when model evals run
    ab_results.jsonl             # present when model evals run
    agent_eval_results.jsonl     # present when Claude/Codex runs agent-orchestrated eval
  summary.md
  summary.html
```

### Trigger eval

Trigger eval consumes each skill's `eval_cases.jsonl`.

- `should_call` checks whether the expected skill is triggered.
- `should_not_call` checks whether a forbidden skill is avoided.
- The summary includes a confusion matrix of `expected_skill -> actual_triggered_skill`.

```bash
# Run trigger eval for one skill
python -m tests.skill_eval.trigger_eval --root . --skill clickzetta-dynamic-table --runs 3 --summary

# Run trigger eval for all skills
python -m tests.skill_eval.trigger_eval --root . --all --runs 3 --summary
```

### A/B uplift eval

A/B eval compares the same user request in two modes:

- `with_skill`: the target skill is available and should be used when helpful.
- `baseline`: the target skill is not used.

The result classifies cases as:

- `high_value`: with-skill passes, baseline fails
- `neutral`: both pass
- `regression`: baseline passes, with-skill fails
- `both_fail`: both fail

```bash
python -m tests.skill_eval.ab_eval --root . --skill clickzetta-dynamic-table --summary
python -m tests.skill_eval.ab_eval --root . --all --summary
```

### Running model-backed evals

Trigger and A/B evals need an external agent command. Configure it with `SKILL_EVAL_AGENT_COMMAND` or pass `--agent-command`.

The command template can use:

- `{prompt_file}`: path to a temporary file containing the prompt
- `{prompt}`: prompt text, only use this when your command template can safely handle multiline arguments
- `{skill_name}`: current skill name
- `{skills_root}`: repository root
- `{skill_path}`: skill directory path, for A/B eval
- `{case_id}`: eval case ID
- `{mode}`: `with_skill` or `baseline`, for A/B eval

If neither `{prompt_file}` nor `{prompt}` is present, the framework appends the prompt as the final argv argument. This is the recommended setup for Claude Code:

```bash
export SKILL_EVAL_AGENT_COMMAND='claude --bare -p --tools Read --output-format stream-json --verbose --include-partial-messages --permission-mode dontAsk --no-session-persistence --max-budget-usd 1'

python -m tests.skill_eval.run_all --root . --include-model-evals --skill clickzetta-dynamic-table --runs 1 --parallelism 3
```

`--parallelism` controls how many independent agent calls run at the same time. Prefer framework-level parallelism over asking one model call to spawn subagents: each case remains isolated, traceable, and easier to score.

`--bare` keeps Claude startup small and makes evals depend on this repository's skills instead of the user's globally installed Claude skills. Trigger eval prompts include the repository skill catalog and ask Claude to read the relevant `SKILL.md`.

For agents that can read a prompt file, use `{prompt_file}` explicitly:

```bash
export SKILL_EVAL_AGENT_COMMAND='your-agent-command --prompt-file {prompt_file}'

python -m tests.skill_eval.run_all --root . --include-model-evals --runs 3
```

Start with `--skill <one-skill-name> --runs 1 --parallelism 2` or `--parallelism 3` to verify the command and cost profile before running `--all`, increasing runs, or using higher parallelism.

If no agent command is configured, `run_all` still produces static validation and overlap reports.

### Agent-orchestrated eval

This is the preferred path when you want Claude/Codex to run the model-backed evals directly and use parallel subagents/workers. It avoids a Python loop repeatedly launching an external agent CLI for every prompt.

Run from an agent session:

```text
按 /Users/guanyangw/clickzetta-skills-dev/tests/agent_eval/RUNBOOK.md
对 /Users/guanyangw/clickzetta-skills-dev 运行完整 skill eval。
尽量使用并行子 agent。
最后生成 summary.md 和 summary.html，并告诉我绝对路径。
```

The agent runbook defines:

- `RUNBOOK.md`: full orchestration steps.
- `WORKER_PROMPT.md`: worker/subagent task template.
- `RESULT_SCHEMA.md`: required `raw/agent_eval_results.jsonl` format.
- `ORCHESTRATOR_PROMPT.md`: copyable prompt for Claude/Codex.

Agent-orchestrated results are written to:

```text
reports/skill-eval-YYYYMMDD-HHMMSS/raw/agent_eval_results.jsonl
```

Then regenerate the report:

```bash
python -m tests.skill_eval.report --root . --report-dir reports/skill-eval-YYYYMMDD-HHMMSS
```

The report will show an **Agent-Orchestrated Eval** section with agent trigger recall, negative pass rate, A/B classifications, average uplift, trigger failures, and an agent confusion matrix.

## Skill Confusion and Duplication Detection

The framework detects skill-boundary issues in several ways:

1. **Trigger confusion matrix**: model-backed trigger eval records `expected_skill -> actual_triggered_skill`. Non-diagonal entries indicate confusion or over-triggering.
2. **Negative cases**: `should_not_call` cases catch obvious over-triggering.
3. **Cross-skill overlap analysis**: `overlap.py` compares descriptions and eval prompts across skills using text similarity.
4. **A/B uplift comparison**: if two skills both solve the same cases equally well, they may overlap. If using both lowers quality, their instructions may conflict.
5. **Agent-orchestrated judging**: Claude/Codex workers can record selected skills, evidence, failure reasons, and with-skill/baseline differences in `agent_eval_results.jsonl`.

The overlap results appear in `summary.md` and `summary.html` under "Potential Overlap".

## Eval Case Format

Each skill can define `eval_cases.jsonl` in its directory. Each line is one JSON object.

Minimal positive case:

```json
{"case_id":"001","type":"should_call","user_input":"怎么创建 Dynamic Table？","expected_skill":"clickzetta-dynamic-table","expected_output_contains":["DYNAMIC TABLE"]}
```

Minimal negative case:

```json
{"case_id":"008","type":"should_not_call","user_input":"帮我写一个 Node.js 后端","forbidden_skill":"clickzetta-dynamic-table"}
```

Supported assertion fields:

- `expected_output_contains`: list of required substrings
- `expected_output_not_contains`: list of forbidden substrings
- `assertions`: optional structured assertions, currently supporting `contains`, `not_contains`, and `regex`

Example:

```json
{
  "case_id": "003",
  "type": "should_call",
  "user_input": "动态表怎么修改刷新间隔和 vcluster？",
  "expected_skill": "clickzetta-dynamic-table",
  "expected_output_contains": ["ALTER", "DYNAMIC TABLE"],
  "expected_output_not_contains": ["TARGET_LAG"],
  "assertions": [
    {"type": "contains", "value": "ALTER DYNAMIC TABLE"},
    {"type": "not_contains", "value": "Snowflake"},
    {"type": "regex", "value": "REFRESH\\s+INTERVAL"}
  ]
}
```

## Test Package Layout

| Path | Purpose |
|---|---|
| `conftest.py` | Shared real Lakehouse connection and `run_sql` helper |
| `test_static_skill_contract.py` | Static contract pytest entry |
| `skill_eval/core.py` | Shared data models and parsers |
| `skill_eval/static_validation.py` | Static validation implementation |
| `skill_eval/agent_runner.py` | External agent command adapter |
| `skill_eval/trigger_eval.py` | Trigger evaluation |
| `skill_eval/ab_eval.py` | With-skill vs baseline evaluation |
| `skill_eval/assertions.py` | Output assertion helpers |
| `skill_eval/overlap.py` | Description and eval-case overlap analysis |
| `skill_eval/agent_orchestrated.py` | Summaries for Claude/Codex-generated agent eval JSONL |
| `skill_eval/report.py` | Markdown and HTML report generation |
| `skill_eval/run_all.py` | Unified evaluation entry point |
| `agent_eval/RUNBOOK.md` | Agent-orchestrated eval instructions |
| `agent_eval/RESULT_SCHEMA.md` | JSONL result contract for agent workers |
| `agent_eval/WORKER_PROMPT.md` | Subagent/worker prompt template |
| `agent_eval/ORCHESTRATOR_PROMPT.md` | Copyable prompt for Claude/Codex |

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
| `test_sql_pipeline_manager.py` | clickzetta-sql-pipeline-manager | Dynamic Table REFRESH interval, MV REFRESH AUTO EVERY, Table Stream, SHOW PIPES |
| `test_dw_modeling.py` | clickzetta-dw-modeling | PARTITIONED BY (days(col)), CLUSTERED BY BUCKETS, Dynamic Table DWS layer, bytes field |

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

1. **Isolated schema**: live product tests run in `skill_test` schema and clean it up after the session.
2. **Negative tests**: wrong syntax is explicitly tested to fail (`expect_error=True`), not just omitted.
3. **Authoritative product validation**: a passing live SQL test means the documented syntax works against ClickZetta.
4. **Skill-as-artifact validation**: `SKILL.md`, index metadata, and eval cases are tested as release artifacts.
5. **Trigger quality matters**: a good skill must be used when relevant and avoided when irrelevant.
6. **Measure uplift**: a skill should improve output quality compared with baseline, not merely exist.
7. **Report everything**: static issues, trigger failures, A/B classifications, and overlap risks should be visible in Markdown and HTML.
