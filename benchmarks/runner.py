#!/usr/bin/env python3
# benchmarks/runner.py
"""
Usage:
  python benchmarks/runner.py --profile billingsh --runs 3
  python benchmarks/runner.py --type multi --runs 1
  python benchmarks/runner.py --case Q1 --runs 1
"""
import argparse
import json
import os
import subprocess
import statistics
import time
from datetime import datetime
from pathlib import Path

import yaml

from parser import parse_stream_json
from scorer import compute_context_transfer_score

BASE = Path(__file__).parent
CASES_FILE = BASE / "test_cases.yaml"
PROMPTS_DIR = BASE / "system_prompts"
RESULTS_DIR = BASE / "results"


def load_cases(case_id=None, case_type=None):
    with open(CASES_FILE) as f:
        data = yaml.safe_load(f)
    cases = data["cases"]
    if case_id:
        cases = [c for c in cases if c["id"] == case_id]
    if case_type:
        cases = [c for c in cases if c["type"] == case_type]
    return cases


def build_claude_cmd(prompt: str, system_prompt_file: Path, profile: str) -> list[str]:
    system_prompt = system_prompt_file.read_text()
    cmd = [
        "claude", "-p", prompt,
        "--bare",
        "--system-prompt", system_prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
    ]
    if profile:
        cmd += ["--append-system-prompt", f"Use cz-cli profile: {profile}"]
    return cmd


def run_single_step(prompt: str, system_prompt_file: Path, profile: str) -> dict:
    """Run one claude subprocess and return parsed result."""
    cmd = build_claude_cmd(prompt, system_prompt_file, profile)
    start = time.monotonic()
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )
    elapsed_ms = int((time.monotonic() - start) * 1000)

    jsonl = proc.stdout
    result = parse_stream_json(jsonl)

    result["wall_time_ms"] = max(elapsed_ms, result.get("total_time_ms", 0))
    result["raw_jsonl"] = jsonl
    return result


def run_case_single(case: dict, approach: str, profile: str, run_idx: int) -> dict:
    """Run a single-step case for one approach."""
    sp_file = PROMPTS_DIR / f"{approach}_mode.md"
    step = case["steps"][0]
    result = run_single_step(step["prompt"], sp_file, profile)
    return {
        "case_id": case["id"],
        "approach": approach,
        "run": run_idx,
        "type": "single",
        "total_time_ms": result["wall_time_ms"],
        "tool_call_count": result["tool_call_count"],
        "tool_sequence": result["tool_sequence"],
        "agent_run_count": result["agent_run_count"],
        "final_output": result["final_output"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }


def run_case_multi(case: dict, approach: str, profile: str, run_idx: int) -> dict:
    """Run a multi-step case, threading prev_output into each subsequent step."""
    sp_file = PROMPTS_DIR / f"{approach}_mode.md"
    steps_results = []
    prev_output = ""
    total_time = 0

    for i, step in enumerate(case["steps"]):
        prompt = step["prompt"].replace("{prev_output}", prev_output)
        result = run_single_step(prompt, sp_file, profile)
        total_time += result["wall_time_ms"]

        step_data = {
            "step": i + 1,
            "prompt_preview": prompt[:100],
            "total_time_ms": result["wall_time_ms"],
            "tool_call_count": result["tool_call_count"],
            "tool_sequence": result["tool_sequence"],
            "agent_run_count": result["agent_run_count"],
            "final_output": result["final_output"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
        }

        if step.get("check_context_transfer") and i > 0:
            prev_step = case["steps"][i - 1]
            patterns = prev_step.get("key_values_for_next", [])
            score, found, expected = compute_context_transfer_score(
                result["final_output"], patterns
            )
            step_data["context_transfer_score"] = score
            step_data["context_transfer_found"] = found
            step_data["context_transfer_expected"] = expected

        steps_results.append(step_data)
        prev_output = result["final_output"]

    return {
        "case_id": case["id"],
        "approach": approach,
        "run": run_idx,
        "type": "multi",
        "total_time_ms": total_time,
        "steps": steps_results,
    }


def aggregate_runs(runs: list[dict]) -> dict:
    """Compute median total_time_ms across runs."""
    times = [r["total_time_ms"] for r in runs]
    return {
        "median_time_ms": int(statistics.median(times)),
        "min_time_ms": min(times),
        "max_time_ms": max(times),
        "runs": runs,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--case", default=None)
    parser.add_argument("--type", dest="case_type", default=None,
                        choices=["single", "multi"])
    args = parser.parse_args()

    cases = load_cases(case_id=args.case, case_type=args.case_type)
    if not cases:
        print("No matching cases found.")
        return

    run_id = datetime.now().strftime("%Y-%m-%d-%H-%M")
    out_dir = RESULTS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results = []

    for case in cases:
        print(f"\n=== Case {case['id']} ({case['type']}) ===")
        for approach in ("direct", "agent_run"):
            print(f"  [{approach}] running {args.runs} time(s)...")
            runs = []
            for i in range(args.runs):
                print(f"    run {i+1}/{args.runs}...", end=" ", flush=True)
                if case["type"] == "single":
                    r = run_case_single(case, approach, args.profile, i + 1)
                else:
                    r = run_case_multi(case, approach, args.profile, i + 1)
                print(f"{r['total_time_ms']}ms")

                raw_file = out_dir / f"{case['id']}_{approach}_run{i+1}.json"
                raw_file.write_text(json.dumps(r, ensure_ascii=False, indent=2))
                runs.append(r)

            agg = aggregate_runs(runs)
            agg["case_id"] = case["id"]
            agg["approach"] = approach
            agg["case_type"] = case["type"]
            all_results.append(agg)
            print(f"    median: {agg['median_time_ms']}ms")

    summary_file = out_dir / "summary.json"
    summary_file.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
    print(f"\nResults saved to {out_dir}/")
    print(f"Run report generator: python benchmarks/report.py {out_dir}/summary.json")


if __name__ == "__main__":
    main()
