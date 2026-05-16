# Agent-Orchestrated Skill Eval Runbook

This runbook lets Claude, Codex, or another coding agent run the model-backed
parts of the ClickZetta skill eval suite directly. It avoids repeatedly
starting an external CLI process for each prompt. The agent should use parallel
subagents/workers when available, write structured JSONL, then call the existing
report generator.

## Goal

Evaluate whether each `clickzetta-*` skill is useful and well-bounded in a real
agent workflow:

- Does the agent select the expected skill for `should_call` cases?
- Does it avoid the forbidden skill for `should_not_call` cases?
- Does using the skill improve the answer compared with a baseline answer?
- Do multiple skills appear confusing or duplicated?

## Inputs

- Repository root: the current `clickzetta-skills-dev` directory.
- Skill directories: folders named `clickzetta-*` with `SKILL.md`.
- Eval cases: each skill's `eval_cases.jsonl`.
- Static/overlap/report scripts: `tests/skill_eval/*`.

## Output Layout

Create a timestamped report directory:

```text
reports/skill-eval-YYYYMMDD-HHMMSS/
  raw/
    static_results.json
    agent_eval_results.jsonl
  summary.md
  summary.html
```

The report generator also understands the older script-generated files:
`trigger_results.jsonl` and `ab_results.jsonl`.

## Recommended Agent Flow

1. Run static/report scaffolding once:

   ```bash
   python3 -m tests.skill_eval.run_all --root . --report-root reports
   ```

   Use the printed report directory as `<REPORT_DIR>`.

2. Read `tests/agent_eval/WORKER_PROMPT.md` and `tests/agent_eval/RESULT_SCHEMA.md`.

3. Load eval cases from `eval_cases.jsonl`.

4. Dispatch parallel workers. Recommended granularity:

   - Small run: one worker per skill.
   - Large run: one worker per 3-5 cases.
   - Keep each worker isolated; do not let workers share conclusions.

5. For each eval case, run three checks:

   - `trigger`: decide which skill(s) should be used for the user request.
   - `with_skill`: answer while reading/using the target skill if helpful.
   - `baseline`: answer without reading/using the target skill.

   For `should_not_call` cases, `trigger` is required and A/B modes are optional.

6. Workers return JSON objects only. The orchestrator appends each object as one
   line to:

   ```text
   <REPORT_DIR>/raw/agent_eval_results.jsonl
   ```

7. Regenerate the report:

   ```bash
   python3 -m tests.skill_eval.report --root . --report-dir <REPORT_DIR>
   ```

8. Inspect:

   ```text
   <REPORT_DIR>/summary.md
   <REPORT_DIR>/summary.html
   ```

## Important Guardrails

- Do not expose `expected_skill` or `forbidden_skill` to trigger workers before
  they choose skills. The orchestrator may add those fields to the final row
  after the worker returns.
- For baseline mode, explicitly tell the worker not to read the target
  `SKILL.md`. It may use general knowledge and non-target files if needed.
- For with-skill mode, explicitly tell the worker to read the target `SKILL.md`
  before answering.
- Keep raw answers and concise judge rationale in the JSONL row. Reports need
  both the score and the explanation.
- Prefer deterministic, evidence-backed judgments over free-form prose.

## Minimal Completion Criteria

A successful agent-orchestrated run produces:

- `raw/agent_eval_results.jsonl`
- Agent trigger pass rate in `summary.md` / `summary.html`
- Agent confusion matrix in `summary.md` / `summary.html`
- Agent A/B classification and average uplift in `summary.md` / `summary.html`

