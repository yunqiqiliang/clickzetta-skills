# Orchestrator Prompt

Use this prompt in Claude/Codex when you want the agent to run the full
agent-orchestrated skill eval.

```text
Run the ClickZetta skill evaluation using tests/agent_eval/RUNBOOK.md.

Repository root:
/Users/guanyangw/clickzetta-skills-dev

Requirements:
- Use parallel subagents/workers when available.
- Do not call an external agent CLI once per case.
- Run static validation/report scaffolding first.
- Load eval cases from each clickzetta-*/eval_cases.jsonl.
- For each case, create rows in raw/agent_eval_results.jsonl using
  tests/agent_eval/RESULT_SCHEMA.md.
- For should_call cases, run trigger, with_skill, and baseline modes.
- For should_not_call cases, run trigger mode; A/B modes are optional.
- Do not reveal expected_skill/forbidden_skill to trigger workers until after
  they select skills.
- Regenerate summary.md and summary.html with:
  python3 -m tests.skill_eval.report --root . --report-dir <REPORT_DIR>
- Finish by reporting the absolute paths to summary.md and summary.html.
```

