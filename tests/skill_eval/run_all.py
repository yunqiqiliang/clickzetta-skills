"""Orchestrate static validation, optional model evals, and report generation."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from .ab_eval import run_ab_eval
from .report import write_report
from .static_validation import validate_repo
from .trigger_eval import run_trigger_eval


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ClickZetta skill evaluation suite.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--report-root", default="reports", help="Directory where eval reports are written.")
    parser.add_argument("--skill", help="Limit model evals to one skill.")
    parser.add_argument("--runs", type=int, default=1, help="Trigger eval runs per case.")
    parser.add_argument("--agent-command", help="Command template for model evals.")
    parser.add_argument("--include-model-evals", action="store_true", help="Run trigger and A/B evals.")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--parallelism", type=int, default=1, help="Concurrent agent calls for model evals.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_dir = (root / args.report_root / f"skill-eval-{stamp}").resolve()
    raw_dir = report_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    static_issues = validate_repo(root)
    (raw_dir / "static_results.json").write_text(
        json.dumps([issue.__dict__ for issue in static_issues], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    agent_command = args.agent_command or os.environ.get("SKILL_EVAL_AGENT_COMMAND")
    if args.include_model_evals:
        trigger_rows = run_trigger_eval(
            root,
            skill_name=args.skill,
            runs=args.runs,
            agent_command=agent_command,
            timeout=args.timeout,
            parallelism=args.parallelism,
        )
        with (raw_dir / "trigger_results.jsonl").open("w", encoding="utf-8") as f:
            for row in trigger_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        ab_rows = run_ab_eval(
            root,
            skill_name=args.skill,
            agent_command=agent_command,
            timeout=args.timeout,
            parallelism=args.parallelism,
        )
        with (raw_dir / "ab_results.jsonl").open("w", encoding="utf-8") as f:
            for row in ab_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_report(report_dir, root)
    print(f"Report written to {report_dir}")
    print(f"- {report_dir / 'summary.md'}")
    print(f"- {report_dir / 'summary.html'}")
    return 1 if any(issue.severity == "error" for issue in static_issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
