"""Trigger evaluation for ClickZetta skills."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .agent_runner import run_agent_command
from .core import EvalCase, iter_skill_dirs, load_all_eval_cases, load_skill, normalize_description


TRIGGER_PROMPT = """You are evaluating skill routing for a local skill repository.

Available skills:
{skill_catalog}

Instructions:
- Decide whether the user request should use one of the available skills.
- If a skill is relevant, read its SKILL.md from the listed path before answering.
- Do not read or use unrelated skills.
- Answer the user request normally after selecting any relevant skill.

User request:
{user_input}
"""


def _case_passed(case: EvalCase, triggered: list[str]) -> bool:
    triggered_set = set(triggered)
    if case.case_type == "should_call":
        return bool(case.expected_skill and case.expected_skill in triggered_set)
    if case.case_type == "should_not_call":
        return bool(case.forbidden_skill and case.forbidden_skill not in triggered_set)
    return False


def _skill_catalog(root: Path) -> str:
    rows: list[str] = []
    for skill_dir in iter_skill_dirs(root):
        skill, _issue = load_skill(skill_dir)
        description = normalize_description(skill.frontmatter.get("description", "")) if skill else ""
        if len(description) > 240:
            description = description[:237].rstrip() + "..."
        rows.append(f"- {skill_dir.name}: {description} ({skill_dir / 'SKILL.md'})")
    return "\n".join(rows)


def run_trigger_eval(
    root: Path,
    *,
    skill_name: str | None = None,
    runs: int = 1,
    agent_command: str | None = None,
    timeout: int = 180,
    parallelism: int = 1,
) -> list[dict[str, Any]]:
    cases, _ = load_all_eval_cases(root, skill_name)
    known_skills = [p.name for p in iter_skill_dirs(root)]
    skill_catalog = _skill_catalog(root)
    trigger_cases = [case for case in cases if case.case_type in {"should_call", "should_not_call"}]
    results_by_index: dict[int, dict[str, Any]] = {}

    def run_one(case_index: int, case: EvalCase, run_index: int) -> tuple[int, int, dict[str, Any]]:
        prompt = TRIGGER_PROMPT.format(skill_catalog=skill_catalog, user_input=case.user_input)
        agent_run = run_agent_command(
            prompt,
            known_skills,
            agent_command,
            timeout=timeout,
            cwd=root,
            extra_placeholders={
                "skill_name": case.skill_name,
                "skills_root": str(root),
                "case_id": case.case_id,
            },
        )
        triggered = agent_run.triggered_skills
        passed = agent_run.status == "completed" and _case_passed(case, triggered)
        return (
            case_index,
            run_index,
            {
                "run": run_index,
                "status": agent_run.status,
                "returncode": agent_run.returncode,
                "triggered_skills": triggered,
                "passed": passed,
                "error": agent_run.error,
            },
        )

    with ThreadPoolExecutor(max_workers=max(1, parallelism)) as executor:
        futures = [
            executor.submit(run_one, case_index, case, run_index)
            for case_index, case in enumerate(trigger_cases)
            for run_index in range(1, runs + 1)
        ]
        grouped: dict[int, list[dict[str, Any]]] = {idx: [] for idx in range(len(trigger_cases))}
        for future in as_completed(futures):
            case_index, _run_index, row = future.result()
            grouped[case_index].append(row)

    for case_index, case in enumerate(trigger_cases):
        run_rows = sorted(grouped[case_index], key=lambda row: row["run"])
        pass_count = sum(int(row["passed"]) for row in run_rows)
        all_triggered = [
            skill
            for row in run_rows
            for skill in row["triggered_skills"]
        ]
        threshold = max(1, (runs + 1) // 2)
        results_by_index[case_index] = (
            {
                "skill": case.skill_name,
                "case_id": case.case_id,
                "type": case.case_type,
                "user_input": case.user_input,
                "expected_skill": case.expected_skill,
                "forbidden_skill": case.forbidden_skill,
                "runs": run_rows,
                "triggered_skills": sorted(set(all_triggered)),
                "pass_count": pass_count,
                "run_count": runs,
                "passed": pass_count >= threshold,
            }
        )
    return [results_by_index[idx] for idx in sorted(results_by_index)]


def summarize_trigger_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    should_call = [r for r in rows if r["type"] == "should_call"]
    should_not = [r for r in rows if r["type"] == "should_not_call"]
    recall = sum(r["passed"] for r in should_call) / len(should_call) if should_call else None
    negative_pass = sum(r["passed"] for r in should_not) / len(should_not) if should_not else None
    confusion: dict[str, dict[str, int]] = {}
    for row in should_call:
        expected = row.get("expected_skill") or row["skill"]
        confusion.setdefault(expected, {})
        actuals = row.get("triggered_skills") or ["<none>"]
        for actual in actuals:
            confusion[expected][actual] = confusion[expected].get(actual, 0) + 1
    return {
        "case_count": len(rows),
        "should_call_count": len(should_call),
        "should_not_call_count": len(should_not),
        "trigger_recall": recall,
        "negative_pass_rate": negative_pass,
        "failed_cases": [r for r in rows if not r["passed"]],
        "confusion_matrix": confusion,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Skill trigger evals.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--skill", help="Only run cases for one skill.")
    parser.add_argument("--all", action="store_true", help="Run all skills.")
    parser.add_argument("--runs", type=int, default=1, help="Runs per case.")
    parser.add_argument("--agent-command", help="Command template. Use {prompt_file}, {skill_name}, {skills_root}.")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--parallelism", type=int, default=1, help="Concurrent agent calls.")
    parser.add_argument("--output", help="Write JSONL results to this path.")
    parser.add_argument("--summary", action="store_true", help="Print summary JSON instead of JSONL rows.")
    args = parser.parse_args(argv)
    if not args.all and not args.skill:
        parser.error("Pass --all or --skill")
    rows = run_trigger_eval(
        Path(args.root).resolve(),
        skill_name=args.skill,
        runs=args.runs,
        agent_command=args.agent_command,
        timeout=args.timeout,
        parallelism=args.parallelism,
    )
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if args.summary:
        print(json.dumps(summarize_trigger_results(rows), ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
