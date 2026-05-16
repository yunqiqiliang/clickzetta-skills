# Agent Eval Result Schema

Write one JSON object per line to `raw/agent_eval_results.jsonl`.

## Common Fields

```json
{
  "schema_version": "agent-eval-v1",
  "skill": "clickzetta-dynamic-table",
  "case_id": "001",
  "case_type": "should_call",
  "mode": "trigger",
  "worker_id": "worker-1",
  "user_input": "用户原始请求",
  "expected_skill": "clickzetta-dynamic-table",
  "forbidden_skill": null,
  "selected_skills": ["clickzetta-dynamic-table"],
  "used_skill": true,
  "passed": true,
  "score": 1.0,
  "answer": "worker 的回答或触发判断摘要",
  "evidence": "为什么这样判断，引用读过的 skill 或关键输出",
  "failure_reason": ""
}
```

## Field Meaning

- `schema_version`: must be `agent-eval-v1`.
- `skill`: owner skill folder for the eval case.
- `case_id`: case ID from `eval_cases.jsonl`.
- `case_type`: `should_call` or `should_not_call`.
- `mode`: one of `trigger`, `with_skill`, `baseline`.
- `worker_id`: stable worker label or subagent label.
- `user_input`: original case request.
- `expected_skill`: expected skill for `should_call`; added by orchestrator.
- `forbidden_skill`: forbidden skill for `should_not_call`; added by orchestrator.
- `selected_skills`: skills the worker actually selected or used.
- `used_skill`: whether the mode used the target skill.
- `passed`: boolean judgment for this row.
- `score`: 0-1 quality score. Use 1 for clearly passed, 0 for clearly failed,
  and middle values for partial answers.
- `answer`: raw answer or concise answer summary.
- `evidence`: concise rationale for the judgment.
- `failure_reason`: empty string when passed; otherwise a short explanation.

## Passing Rules

For `trigger` mode:

- `should_call` passes when `expected_skill` is in `selected_skills`.
- `should_not_call` passes when `forbidden_skill` is not in `selected_skills`.

For `with_skill` and `baseline` modes:

- Evaluate the answer against `expected_output_contains`,
  `expected_output_not_contains`, and any structured assertions in the case.
- `with_skill` should normally use/read the target skill.
- `baseline` should not read/use the target skill.

## A/B Uplift

The report groups rows by `(skill, case_id)`:

- `high_value`: with-skill passed, baseline failed.
- `neutral`: both passed.
- `regression`: with-skill failed, baseline passed.
- `both_fail`: both failed.

Average uplift is:

```text
with_skill_pass_rate - baseline_pass_rate
```

