#!/usr/bin/env python3
# benchmarks/report.py
import json
import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).parent
TEMPLATES_DIR = BASE / "templates"
REPORTS_DIR = BASE / "reports"


def build_summary_rows(results: list[dict]) -> list[dict]:
    by_case = {}
    for r in results:
        cid = r["case_id"]
        if cid not in by_case:
            by_case[cid] = {}
        by_case[cid][r["approach"]] = r

    rows = []
    for cid, approaches in by_case.items():
        d = approaches.get("direct", {})
        a = approaches.get("agent_run", {})
        d_ms = d.get("median_time_ms", 0)
        a_ms = a.get("median_time_ms", 0)
        ratio = round(a_ms / d_ms, 1) if d_ms else "—"

        d_tools = _median_tool_count(d.get("runs", []))
        a_tools = _median_tool_count(a.get("runs", []))

        rows.append({
            "case_id": cid,
            "case_type": d.get("case_type", a.get("case_type", "")),
            "direct_ms": d_ms,
            "agent_ms": a_ms,
            "ratio": ratio,
            "direct_tools": d_tools,
            "agent_tools": a_tools,
        })
    return rows


def _median_tool_count(runs: list[dict]) -> int:
    if not runs:
        return 0
    counts = []
    for r in runs:
        if r.get("type") == "single":
            counts.append(r.get("tool_call_count", 0))
        else:
            counts.append(sum(s.get("tool_call_count", 0) for s in r.get("steps", [])))
    return int(sorted(counts)[len(counts) // 2])


def build_timeline_rows(results: list[dict]) -> list[dict]:
    by_case = {}
    for r in results:
        cid = r["case_id"]
        if cid not in by_case:
            by_case[cid] = {}
        by_case[cid][r["approach"]] = r

    rows = []
    max_ms = max(
        (r.get("median_time_ms", 0) for r in results), default=1
    )
    scale = 400 / max_ms if max_ms else 1

    for cid, approaches in by_case.items():
        d = approaches.get("direct", {})
        a = approaches.get("agent_run", {})
        d_ms = d.get("median_time_ms", 0)
        a_ms = a.get("median_time_ms", 0)

        d_seq = _first_run_seq(d.get("runs", []))
        a_seq = _first_run_seq(a.get("runs", []))

        rows.append({
            "case_id": cid,
            "direct_ms": d_ms,
            "agent_ms": a_ms,
            "direct_bar_px": int(d_ms * scale),
            "agent_bar_px": int(a_ms * scale),
            "direct_seq": " → ".join(d_seq) if d_seq else "—",
            "agent_seq": " → ".join(a_seq) if a_seq else "—",
        })
    return rows


def _first_run_seq(runs: list[dict]) -> list[str]:
    if not runs:
        return []
    r = runs[0]
    if r.get("type") == "single":
        return r.get("tool_sequence", [])
    seqs = []
    for s in r.get("steps", []):
        seqs.extend(s.get("tool_sequence", []))
    return seqs


def build_context_rows(results: list[dict]) -> list[dict]:
    by_case = {}
    for r in results:
        cid = r["case_id"]
        if cid not in by_case:
            by_case[cid] = {}
        by_case[cid][r["approach"]] = r

    rows = []
    for cid, approaches in by_case.items():
        d = approaches.get("direct", {})
        a = approaches.get("agent_run", {})
        if d.get("case_type") != "multi":
            continue

        d_steps = d.get("runs", [{}])[0].get("steps", [])
        a_steps = a.get("runs", [{}])[0].get("steps", [])

        for i, (ds, as_) in enumerate(zip(d_steps, a_steps)):
            if "context_transfer_score" not in ds:
                continue
            rows.append({
                "case_id": cid,
                "step": i + 1,
                "direct_score": ds.get("context_transfer_score", 0),
                "agent_score": as_.get("context_transfer_score", 0),
                "expected": ds.get("context_transfer_expected", 0),
                "direct_found": ds.get("context_transfer_found", []),
                "agent_found": as_.get("context_transfer_found", []),
            })
    return rows


def render_report(summary_file: Path) -> Path:
    results = json.loads(summary_file.read_text())
    run_id = summary_file.parent.name

    total_cases = len({r["case_id"] for r in results})
    runs_per_case = max((len(r.get("runs", [])) for r in results), default=0)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    tmpl = env.get_template("report.html.j2")

    html = tmpl.render(
        run_id=run_id,
        total_cases=total_cases,
        runs_per_case=runs_per_case,
        summary_rows=build_summary_rows(results),
        timeline_rows=build_timeline_rows(results),
        context_rows=build_context_rows(results),
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"{run_id}.html"
    out.write_text(html)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python benchmarks/report.py <path/to/summary.json>")
        sys.exit(1)
    out = render_report(Path(sys.argv[1]))
    print(f"Report written to {out}")
