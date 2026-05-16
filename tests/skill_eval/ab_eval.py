"""With-skill vs baseline evaluation."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .agent_runner import run_agent_command
from .assertions import evaluate_output, result_to_dict
from .core import iter_skill_dirs, load_all_eval_cases


WITH_SKILL_PROMPT = """Use the ClickZetta skill at {skill_path} if it is helpful for this request.

User request:
{user_input}
"""

BASELINE_PROMPT = """Answer the following ClickZetta user request without reading or using the skill at {skill_path}.

User request:
{user_input}
"""


def run_ab_eval(
    root: Path,
    *,
    skill_name: str | None = None,
    agent_command: str | None = None,
    timeout: int = 240,
    parallelism: int = 1,
) -> list[dict[str, Any]]:
    cases, _ = load_all_eval_cases(root, skill_name)
    known_skills = [p.name for p in iter_skill_dirs(root)]
    ab_cases = [case for case in cases if case.case_type == "should_call"]
    results_by_index: dict[int, dict[str, Any]] = {
        case_index: {
            "skill": case.skill_name,
            "case_id": case.case_id,
            "user_input": case.user_input,
            "expected_skill": case.expected_skill,
            "modes": {},
        }
        for case_index, case in enumerate(ab_cases)
    }

    def run_one(case_index: int, mode: str, prompt: str) -> tuple[int, str, dict[str, Any]]:
        case = ab_cases[case_index]
        skill_path = root / case.skill_name
        agent_run = run_agent_command(
            prompt,
            known_skills,
            agent_command,
            timeout=timeout,
            cwd=root,
            extra_placeholders={
                "skill_name": case.skill_name,
                "skills_root": str(root),
                "skill_path": str(skill_path),
                "case_id": case.case_id,
                "mode": mode,
            },
        )
        assertion = evaluate_output(agent_run.output, case) if agent_run.status == "completed" else None
        return (
            case_index,
            mode,
            {
                "status": agent_run.status,
                "returncode": agent_run.returncode,
                "triggered_skills": agent_run.triggered_skills,
                "passed": bool(assertion and assertion.passed),
                "assertions": result_to_dict(assertion) if assertion else {"passed": False, "failures": [agent_run.error]},
                "error": agent_run.error,
            },
        )

    with ThreadPoolExecutor(max_workers=max(1, parallelism)) as executor:
        futures = []
        for case_index, case in enumerate(ab_cases):
            skill_path = root / case.skill_name
            prompts = {
                "with_skill": WITH_SKILL_PROMPT.format(skill_path=skill_path, user_input=case.user_input),
                "baseline": BASELINE_PROMPT.format(skill_path=skill_path, user_input=case.user_input),
            }
            for mode, prompt in prompts.items():
                futures.append(executor.submit(run_one, case_index, mode, prompt))
        for future in as_completed(futures):
            case_index, mode, mode_result = future.result()
            results_by_index[case_index]["modes"][mode] = mode_result

    results: list[dict[str, Any]] = []
    for case_index in sorted(results_by_index):
        row = results_by_index[case_index]
        with_pass = row["modes"]["with_skill"]["passed"]
        base_pass = row["modes"]["baseline"]["passed"]
        row["uplift"] = int(with_pass) - int(base_pass)
        row["classification"] = (
            "high_value" if with_pass and not base_pass else
            "neutral" if with_pass and base_pass else
            "regression" if base_pass and not with_pass else
            "both_fail"
        )
        results.append(row)
    return results


def summarize_ab_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    if not total:
        return {"case_count": 0}
    with_rate = sum(row["modes"]["with_skill"]["passed"] for row in rows) / total
    baseline_rate = sum(row["modes"]["baseline"]["passed"] for row in rows) / total
    by_class: dict[str, int] = {}
    for row in rows:
        by_class[row["classification"]] = by_class.get(row["classification"], 0) + 1
    return {
        "case_count": total,
        "with_skill_pass_rate": with_rate,
        "baseline_pass_rate": baseline_rate,
        "average_uplift": with_rate - baseline_rate,
        "classification_counts": by_class,
        "regression_cases": [row for row in rows if row["classification"] == "regression"],
        "both_fail_cases": [row for row in rows if row["classification"] == "both_fail"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run with-skill vs baseline evals.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--skill", help="Only run cases for one skill.")
    parser.add_argument("--all", action="store_true", help="Run all skills.")
    parser.add_argument("--agent-command", help="Command template. Use {prompt_file}, {skill_name}, {mode}.")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--parallelism", type=int, default=1, help="Concurrent agent calls.")
    parser.add_argument("--output", help="Write JSONL results to this path.")
    parser.add_argument("--summary", action="store_true", help="Print summary JSON instead of JSONL rows.")
    args = parser.parse_args(argv)
    if not args.all and not args.skill:
        parser.error("Pass --all or --skill")
    rows = run_ab_eval(
        Path(args.root).resolve(),
        skill_name=args.skill,
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
        print(json.dumps(summarize_ab_results(rows), ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
