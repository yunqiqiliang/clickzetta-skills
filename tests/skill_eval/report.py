"""Markdown and HTML reports for ClickZetta skill eval runs."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from .ab_eval import summarize_ab_results
from .agent_orchestrated import summarize_agent_eval
from .overlap import analyze_overlap
from .static_validation import validate_repo
from .trigger_eval import summarize_trigger_results


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _raw_file_status(report_dir: Path) -> dict[str, bool]:
    raw = report_dir / "raw"
    return {
        "static": (raw / "static_results.json").exists(),
        "trigger": (raw / "trigger_results.jsonl").exists(),
        "ab": (raw / "ab_results.jsonl").exists(),
        "agent": (raw / "agent_eval_results.jsonl").exists(),
    }


def build_report_data(report_dir: Path, root: Path) -> dict[str, Any]:
    raw = report_dir / "raw"
    static_rows = _read_json(raw / "static_results.json", None)
    if static_rows is None:
        static_rows = [issue.__dict__ for issue in validate_repo(root)]
    trigger_rows = _read_jsonl(raw / "trigger_results.jsonl")
    ab_rows = _read_jsonl(raw / "ab_results.jsonl")
    agent_rows = _read_jsonl(raw / "agent_eval_results.jsonl")
    return {
        "static": static_rows,
        "trigger": trigger_rows,
        "trigger_summary": summarize_trigger_results(trigger_rows),
        "ab": ab_rows,
        "ab_summary": summarize_ab_results(ab_rows),
        "agent": agent_rows,
        "agent_summary": summarize_agent_eval(agent_rows),
        "overlap": analyze_overlap(root),
        "raw_files": _raw_file_status(report_dir),
    }


def _interpret_static(errors: int, warnings: int) -> str:
    if errors:
        return "Static validation has blocking errors. Fix these before trusting model evals or publishing skills."
    if warnings:
        return "Static validation has no blocking errors, but warnings show quality debt or incomplete eval coverage."
    return "Static validation found no structural issues."


def _interpret_rate(value: float | None, *, higher_is_better: bool = True) -> str:
    if value is None:
        return "Not available because this eval layer did not run or has no matching cases."
    if higher_is_better:
        if value >= 0.9:
            return "Healthy."
        if value >= 0.7:
            return "Usable, but there is room to improve."
        return "Needs attention."
    if value <= 0.05:
        return "Healthy."
    if value <= 0.2:
        return "Watch this."
    return "Needs attention."


def _has_model_eval_data(data: dict[str, Any]) -> bool:
    raw_files = data.get("raw_files", {})
    return bool(
        data["trigger"] or data["ab"] or data.get("agent") or
        raw_files.get("trigger") or raw_files.get("ab") or raw_files.get("agent")
    )


def render_markdown(data: dict[str, Any]) -> str:
    static_errors = [x for x in data["static"] if x["severity"] == "error"]
    static_warnings = [x for x in data["static"] if x["severity"] == "warning"]
    trigger = data["trigger_summary"]
    ab = data["ab_summary"]
    agent = data["agent_summary"]
    model_eval_note = (
        "Model eval raw files are present."
        if _has_model_eval_data(data)
        else "Model evals did not run for this report. The report still includes static validation and overlap analysis."
    )
    lines = [
        "# ClickZetta Skills Eval Summary",
        "",
        "## How to Read This Report",
        "",
        "This report has five logical layers:",
        "",
        "- **Static validation** checks whether skills are well-formed release artifacts: `SKILL.md`, frontmatter, `.well-known/skills/index.json`, and `eval_cases.jsonl`.",
        "- **Trigger eval** checks whether the agent selects the right skill for `should_call` cases and avoids the forbidden skill for `should_not_call` cases.",
        "- **A/B uplift eval** compares `with_skill` against `baseline` to estimate whether a skill actually improves answer quality.",
        "- **Agent-orchestrated eval** lets Claude/Codex run eval cases with parallel workers and writes `raw/agent_eval_results.jsonl`.",
        "- **Overlap analysis** scans descriptions and eval prompts for likely skill-boundary confusion or duplicated scope.",
        "",
        model_eval_note,
        "",
        "## Overview",
        "",
        f"- Static validation: {len(static_errors)} error(s), {len(static_warnings)} warning(s)",
        f"  - Meaning: {_interpret_static(len(static_errors), len(static_warnings))}",
        f"- Trigger cases: {trigger.get('case_count', 0)}",
        f"- Trigger recall: {_pct(trigger.get('trigger_recall'))}",
        f"  - Meaning: percentage of `should_call` cases where the expected skill was triggered. {_interpret_rate(trigger.get('trigger_recall'))}",
        f"- Negative pass rate: {_pct(trigger.get('negative_pass_rate'))}",
        f"  - Meaning: percentage of `should_not_call` cases where the forbidden skill was avoided. {_interpret_rate(trigger.get('negative_pass_rate'))}",
        f"- A/B cases: {ab.get('case_count', 0)}",
        f"- With-skill pass rate: {_pct(ab.get('with_skill_pass_rate')) if ab.get('case_count') else 'n/a'}",
        f"- Baseline pass rate: {_pct(ab.get('baseline_pass_rate')) if ab.get('case_count') else 'n/a'}",
        f"- Average uplift: {_pct(ab.get('average_uplift')) if ab.get('case_count') else 'n/a'}",
        "  - Meaning: with-skill pass rate minus baseline pass rate. Positive means the skill helped on average.",
        f"- Agent rows: {agent.get('row_count', 0)}",
        f"- Agent trigger recall: {_pct(agent.get('trigger_recall'))}",
        f"  - Meaning: trigger pass rate from `raw/agent_eval_results.jsonl`. {_interpret_rate(agent.get('trigger_recall'))}",
        f"- Agent A/B cases: {agent.get('ab_case_count', 0)}",
        f"- Agent average uplift: {_pct(agent.get('average_uplift')) if agent.get('ab_case_count') else 'n/a'}",
        "  - Meaning: agent-orchestrated with-skill pass rate minus baseline pass rate.",
        "",
        "## Field Glossary",
        "",
        "- `severity`: `error` blocks static validation; `warning` indicates quality debt or incomplete coverage.",
        "- `code`: machine-readable issue category, useful for grouping and automation.",
        "- `skill`: skill folder affected by the row.",
        "- `score`: overlap similarity score between 0 and 1. Higher means two descriptions or prompts share more terms and may need boundary review.",
        "- `shared_terms`: terms that appear in both compared texts and contributed to the overlap score.",
        "- `triggered_skills`: skills detected in the agent/tool trace for a trigger eval case.",
        "- `selected_skills`: skills selected by an agent-orchestrated worker.",
        "- `worker_id`: identifier for the Claude/Codex subagent or worker that produced the row.",
        "- `uplift`: with-skill result minus baseline result for an A/B case.",
        "",
        "## Static Issues",
        "",
        "Static issues explain whether the repository can be treated as a coherent skill release. Errors should be fixed first. Warnings usually indicate missing eval coverage, stale index metadata, or possible quality debt.",
        "",
    ]
    if not data["static"]:
        lines.append("No static issues found.")
    else:
        for issue in data["static"][:200]:
            lines.append(f"- **{issue['severity']}** `{issue['code']}` `{issue.get('skill') or '-'}`: {issue['message']} ({issue['path']})")
    lines.extend(["", "## Trigger Failures", ""])
    lines.append("Trigger failures are cases where the expected skill was not selected, or a forbidden skill was selected. If this section is empty and trigger cases are zero, model-backed trigger eval did not run.")
    lines.append("")
    failed_trigger = trigger.get("failed_cases", [])
    if not failed_trigger:
        lines.append("No trigger failures recorded.")
    else:
        for row in failed_trigger[:100]:
            lines.append(f"- `{row['skill']}#{row['case_id']}` {row['type']}: triggered={row.get('triggered_skills')} input={row['user_input']}")
    lines.extend(["", "## A/B Classifications", ""])
    lines.append("A/B classifications explain whether using a skill improved model output compared with baseline.")
    lines.append("")
    lines.append("- `high_value`: with-skill passed and baseline failed.")
    lines.append("- `neutral`: both with-skill and baseline passed.")
    lines.append("- `regression`: baseline passed but with-skill failed.")
    lines.append("- `both_fail`: both modes failed.")
    lines.append("")
    for key, value in sorted((ab.get("classification_counts") or {}).items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Skill Confusion Matrix", ""])
    lines.append("The confusion matrix is built from trigger evals. Each row means: expected skill -> detected actual skill(s). Non-diagonal entries are the main signal for skill confusion.")
    lines.append("")
    confusion = trigger.get("confusion_matrix") or {}
    if not confusion:
        lines.append("No trigger confusion data recorded.")
    else:
        for expected, actuals in sorted(confusion.items()):
            rendered = ", ".join(f"{actual}: {count}" for actual, count in sorted(actuals.items()))
            lines.append(f"- `{expected}` -> {rendered}")
    lines.extend(["", "## Agent-Orchestrated Eval", ""])
    lines.append("Agent-orchestrated eval is produced when Claude/Codex follows `tests/agent_eval/RUNBOOK.md` and writes `raw/agent_eval_results.jsonl`. It is useful when you want the agent itself to dispatch parallel workers instead of a Python script repeatedly invoking an external CLI.")
    lines.append("")
    if not data.get("agent"):
        lines.append("No agent-orchestrated eval rows recorded.")
    else:
        lines.append(f"- Rows: {agent.get('row_count', 0)}")
        lines.append(f"- Trigger cases: {agent.get('trigger_case_count', 0)}")
        lines.append(f"- Trigger recall: {_pct(agent.get('trigger_recall'))}")
        lines.append(f"- Negative pass rate: {_pct(agent.get('negative_pass_rate'))}")
        lines.append(f"- A/B pairs: {agent.get('ab_case_count', 0)}")
        lines.append(f"- With-skill pass rate: {_pct(agent.get('with_skill_pass_rate'))}")
        lines.append(f"- Baseline pass rate: {_pct(agent.get('baseline_pass_rate'))}")
        lines.append(f"- Average uplift: {_pct(agent.get('average_uplift'))}")
        lines.append("")
        lines.append("### Agent A/B classifications")
        lines.append("")
        for key, value in sorted((agent.get("classification_counts") or {}).items()):
            lines.append(f"- `{key}`: {value}")
        lines.append("")
        lines.append("### Agent confusion matrix")
        lines.append("")
        agent_confusion = agent.get("confusion_matrix") or {}
        if not agent_confusion:
            lines.append("No agent confusion data recorded.")
        else:
            for expected, actuals in sorted(agent_confusion.items()):
                rendered = ", ".join(f"{actual}: {count}" for actual, count in sorted(actuals.items()))
                lines.append(f"- `{expected}` -> {rendered}")
        failed_agent = agent.get("failed_trigger_cases") or []
        if failed_agent:
            lines.append("")
            lines.append("### Agent trigger failures")
            lines.append("")
            for row in failed_agent[:50]:
                lines.append(
                    f"- `{row.get('skill')}#{row.get('case_id')}` {row.get('case_type')}: "
                    f"selected={row.get('selected_skills')} reason={row.get('failure_reason') or row.get('evidence') or ''}"
                )
    lines.extend(["", "## Potential Overlap", ""])
    lines.append("Overlap analysis is heuristic. A high score is not automatically wrong; it is a review signal that two skills may share trigger language, examples, or functional scope.")
    lines.append("")
    desc_overlap = data["overlap"]["description_overlap"][:30]
    case_overlap = data["overlap"]["case_overlap"][:30]
    lines.append("### Description overlap")
    lines.append("")
    lines.append("Description overlap compares skill frontmatter descriptions. `score` is token Jaccard similarity: shared terms divided by all unique terms across the two descriptions.")
    lines.append("")
    if not desc_overlap:
        lines.append("No high description overlap found.")
    else:
        for row in desc_overlap:
            lines.append(f"- `{row['left']}` ↔ `{row['right']}` score={row['score']} shared={', '.join(row['shared_terms'][:8])}")
    lines.append("")
    lines.append("### Eval case overlap")
    lines.append("")
    lines.append("Eval case overlap compares user prompts across different skills. High score means two skills are tested with similar user requests and may need clearer ownership or negative cases.")
    lines.append("")
    if not case_overlap:
        lines.append("No high cross-skill eval case overlap found.")
    else:
        for row in case_overlap:
            lines.append(
                f"- `{row['left_skill']}#{row['left_case_id']}` ↔ `{row['right_skill']}#{row['right_case_id']}` "
                f"score={row['score']}: {row['left_input']} / {row['right_input']}"
            )
    lines.append("")
    return "\n".join(lines)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    cells = ["<table><thead><tr>"]
    cells.extend(f"<th>{html.escape(h)}</th>" for h in headers)
    cells.append("</tr></thead><tbody>")
    for row in rows:
        cells.append("<tr>")
        cells.extend(f"<td>{html.escape(str(cell))}</td>" for cell in row)
        cells.append("</tr>")
    cells.append("</tbody></table>")
    return "".join(cells)


def _explanation_box(title: str, body: str) -> str:
    return f"<section class='explain'><h3>{html.escape(title)}</h3><p>{html.escape(body)}</p></section>"


def _status_class(value: str | int | float | None) -> str:
    text = str(value)
    if text in {"0", "0.0", "0.0%"} or text.lower() == "healthy.":
        return "ok"
    if text == "n/a":
        return "muted"
    return "warn"


def render_html(data: dict[str, Any]) -> str:
    static_errors = [x for x in data["static"] if x["severity"] == "error"]
    static_warnings = [x for x in data["static"] if x["severity"] == "warning"]
    trigger = data["trigger_summary"]
    ab = data["ab_summary"]
    agent = data["agent_summary"]
    cards = [
        ("Static errors", len(static_errors)),
        ("Static warnings", len(static_warnings)),
        ("Trigger recall", _pct(trigger.get("trigger_recall"))),
        ("Negative pass", _pct(trigger.get("negative_pass_rate"))),
        ("With-skill pass", _pct(ab.get("with_skill_pass_rate")) if ab.get("case_count") else "n/a"),
        ("Average uplift", _pct(ab.get("average_uplift")) if ab.get("case_count") else "n/a"),
        ("Agent trigger", _pct(agent.get("trigger_recall"))),
        ("Agent uplift", _pct(agent.get("average_uplift")) if agent.get("ab_case_count") else "n/a"),
    ]
    static_rows = [[x["severity"], x["code"], x.get("skill") or "", x["message"], x["path"]] for x in data["static"][:300]]
    failed_trigger = trigger.get("failed_cases", [])
    trigger_rows = [[x["skill"], x["case_id"], x["type"], ", ".join(x.get("triggered_skills") or []), x["user_input"]] for x in failed_trigger[:200]]
    desc_rows = [[x["left"], x["right"], x["score"], ", ".join(x["shared_terms"][:10])] for x in data["overlap"]["description_overlap"][:100]]
    case_rows = [
        [x["left_skill"], x["left_case_id"], x["right_skill"], x["right_case_id"], x["score"], f"{x['left_input']} / {x['right_input']}"]
        for x in data["overlap"]["case_overlap"][:100]
    ]
    agent_failed_rows = [
        [
            row.get("skill", ""),
            row.get("case_id", ""),
            row.get("case_type", ""),
            ", ".join(row.get("selected_skills") or []),
            row.get("failure_reason") or row.get("evidence") or "",
        ]
        for row in (agent.get("failed_trigger_cases") or [])[:100]
    ]
    agent_ab_rows = [
        [row["skill"], row["case_id"], row["classification"], row["uplift"], row.get("with_evidence", ""), row.get("baseline_evidence", "")]
        for row in (agent.get("ab_pairs") or [])[:100]
    ]
    card_html = "".join(
        f"<section class='card {_status_class(v)}'><div>{html.escape(k)}</div><strong>{html.escape(str(v))}</strong></section>"
        for k, v in cards
    )
    model_eval_note = (
        "本次报告包含模型触发、A/B Eval 或 Agent 编排 Eval 原始结果。"
        if _has_model_eval_data(data)
        else "本次报告没有模型触发/A-B/Agent Eval 原始结果；当前 HTML 主要解释静态校验和 overlap 分析。可配置 SKILL_EVAL_AGENT_COMMAND，或让 Claude/Codex 按 tests/agent_eval/RUNBOOK.md 生成 agent_eval_results.jsonl。"
    )
    static_explanation = _interpret_static(len(static_errors), len(static_warnings))
    trigger_recall_meaning = _interpret_rate(trigger.get("trigger_recall"))
    negative_meaning = _interpret_rate(trigger.get("negative_pass_rate"))
    average_uplift = ab.get("average_uplift") if ab.get("case_count") else None
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClickZetta Skills Eval Summary</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; margin: 0; color: #1f2937; background: #f8fafc; line-height: 1.55; }}
main {{ max-width: 1240px; margin: 0 auto; padding: 28px 22px 56px; }}
h1 {{ margin: 0 0 8px; font-size: 32px; }}
h2 {{ margin: 0 0 14px; font-size: 22px; }}
h3 {{ margin: 0 0 8px; font-size: 16px; }}
p {{ margin: 8px 0; }}
code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; }}
.lead {{ color: #64748b; max-width: 920px; margin-bottom: 18px; }}
.panel {{ background: white; border: 1px solid #dbe3ef; border-radius: 8px; padding: 18px; margin: 16px 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 16px 0 22px; }}
.card {{ background: white; border: 1px solid #dbe3ef; border-radius: 8px; padding: 14px; }}
.card div {{ color: #64748b; font-size: 13px; }}
.card strong {{ display: block; margin-top: 6px; font-size: 24px; }}
.card.ok strong {{ color: #14804a; }}
.card.warn strong {{ color: #a15c00; }}
.card.muted strong {{ color: #64748b; }}
.explain {{ background: #f4f8ff; border: 1px solid #cfe0ff; border-radius: 8px; padding: 13px; margin: 10px 0; }}
.dictionary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; }}
.term {{ background: #fbfcfe; border: 1px solid #dbe3ef; border-radius: 8px; padding: 11px; }}
.term strong {{ display: block; margin-bottom: 4px; }}
table {{ width: 100%; border-collapse: collapse; background: white; margin: 8px 0 28px; font-size: 13px; }}
th, td {{ border: 1px solid #dbe3ef; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}
.empty {{ color: #64748b; background: #fbfcfe; border: 1px dashed #cbd5e1; padding: 12px; border-radius: 8px; }}
ul {{ margin-top: 8px; }}
</style>
</head>
<body>
<main>
<h1>ClickZetta Skills Eval Summary</h1>
<p class="lead">这份报告用于评估 ClickZetta Skill 仓库的结构质量、触发质量、A/B 增益和 Skill 边界重叠。它既是测试结果，也是阅读指南。</p>
<div class="grid">{card_html}</div>

<section class="panel">
<h2>How to Read This Report</h2>
<p>{html.escape(model_eval_note)}</p>
<div class="dictionary">
<div class="term"><strong>Static validation</strong>检查 <code>SKILL.md</code>、frontmatter、index 和 eval case 是否是可发布的 Skill 制品。当前解读：{html.escape(static_explanation)}</div>
<div class="term"><strong>Trigger recall</strong><code>should_call</code> 中成功触发期望 Skill 的比例。当前解读：{html.escape(trigger_recall_meaning)}</div>
<div class="term"><strong>Negative pass</strong><code>should_not_call</code> 中成功避免 forbidden Skill 的比例。当前解读：{html.escape(negative_meaning)}</div>
<div class="term"><strong>Average uplift</strong>with-skill 通过率减去 baseline 通过率。当前值：{html.escape(_pct(average_uplift))}。</div>
<div class="term"><strong>Agent eval</strong>Claude/Codex 按 <code>tests/agent_eval/RUNBOOK.md</code> 并发运行 case 后写入 <code>raw/agent_eval_results.jsonl</code>。当前 Agent rows：{html.escape(str(agent.get("row_count", 0)))}。</div>
<div class="term"><strong>Score</strong>Overlap 相似度，范围 0 到 1。越高表示两个文本共享词越多，越需要检查 Skill 边界。</div>
<div class="term"><strong>Shared terms</strong>两个描述或两个 eval prompt 共同出现的词，是 score 的主要来源。</div>
</div>
</section>

<section class="panel">
<h2>Metric Definitions</h2>
<ul>
<li><strong>Static errors</strong>: 阻塞性结构问题，应优先修复。当前 pytest 只会因 error 失败。</li>
<li><strong>Static warnings</strong>: 质量债或覆盖不足，例如缺少负例、index 元数据不同步、description 偏长。</li>
<li><strong>Trigger cases</strong>: 参与模型触发测试的 case 数量。为 0 通常表示没有运行 model-backed eval。</li>
<li><strong>A/B cases</strong>: 参与 with-skill vs baseline 对比的 case 数量。为 0 通常表示没有运行 model-backed eval。</li>
<li><strong>Agent rows</strong>: 由 Claude/Codex 子 agent 直接生成的结构化评测行，来源是 <code>raw/agent_eval_results.jsonl</code>。</li>
<li><strong>Description overlap</strong>: 比较 Skill frontmatter description，用于发现触发描述是否重叠。</li>
<li><strong>Eval case overlap</strong>: 比较不同 Skill 的用户样例，用于发现测试样例和功能范围是否重叠。</li>
</ul>
</section>

<section class="panel">
<h2>Static Issues</h2>
{_explanation_box("What this table means", "每一行都是一个静态校验发现。Severity 为 error 表示阻塞问题；warning 表示不阻塞当前测试但建议治理。Code 是问题类别，Skill 是受影响的 skill，Message 是具体解释。")}
{_table(["Severity", "Code", "Skill", "Message", "Path"], static_rows)}
</section>

<section class="panel">
<h2>Trigger Failures</h2>
{_explanation_box("What this table means", "该表只在运行 trigger eval 后有内容。它展示应该触发但没触发、或不该触发却触发的 case。Triggered 是从 agent/tool trace 中检测到的实际 Skill。")}
{_table(["Skill", "Case", "Type", "Triggered", "Input"], trigger_rows) if trigger_rows else "<div class='empty'>No trigger failures recorded. If Trigger cases is 0, model-backed trigger eval did not run.</div>"}
</section>

<section class="panel">
<h2>A/B Eval Meaning</h2>
{_explanation_box("Classification guide", "high_value 表示 Skill 帮助明显；neutral 表示两边都能答对；regression 表示使用 Skill 反而变差；both_fail 表示 Skill 和 baseline 都没通过，需要看 case 或 Skill 内容。")}
{_table(["Classification", "Count"], [[k, v] for k, v in sorted((ab.get("classification_counts") or {}).items())]) if (ab.get("classification_counts") or {}) else "<div class='empty'>No A/B classification data. Model-backed A/B eval did not run or produced no cases.</div>"}
</section>

<section class="panel">
<h2>Skill Confusion Matrix</h2>
{_explanation_box("What this section means", "混淆矩阵来自 trigger eval。每一行表示 expected skill -> actual detected skill。对角线是正确触发；非对角线表示 Skill 之间可能混淆或互相抢触发。")}
{"".join(f"<p><code>{html.escape(expected)}</code> -> {html.escape(', '.join(f'{actual}: {count}' for actual, count in sorted(actuals.items())))}</p>" for expected, actuals in sorted((trigger.get("confusion_matrix") or {}).items())) or "<div class='empty'>No confusion matrix data. Trigger eval did not run.</div>"}
</section>

<section class="panel">
<h2>Agent-Orchestrated Eval</h2>
{_explanation_box("What this section means", "这一层来自 Claude/Codex 按 tests/agent_eval/RUNBOOK.md 并发调度子 agent 的结果。它不依赖测试脚本持续向 agent 喂 prompt，而是让 agent 自己执行 trigger、with_skill、baseline 三类任务并写入 raw/agent_eval_results.jsonl。")}
<div class="dictionary">
<div class="term"><strong>Rows</strong>{html.escape(str(agent.get("row_count", 0)))}</div>
<div class="term"><strong>Trigger recall</strong>{html.escape(_pct(agent.get("trigger_recall")))}</div>
<div class="term"><strong>Negative pass</strong>{html.escape(_pct(agent.get("negative_pass_rate")))}</div>
<div class="term"><strong>Average uplift</strong>{html.escape(_pct(agent.get("average_uplift")) if agent.get("ab_case_count") else "n/a")}</div>
</div>
<h3>Agent A/B Pairs</h3>
{_table(["Skill", "Case", "Classification", "Uplift", "With evidence", "Baseline evidence"], agent_ab_rows) if agent_ab_rows else "<div class='empty'>No agent A/B pairs recorded.</div>"}
<h3>Agent Trigger Failures</h3>
{_table(["Skill", "Case", "Type", "Selected skills", "Reason"], agent_failed_rows) if agent_failed_rows else "<div class='empty'>No agent trigger failures recorded.</div>"}
<h3>Agent Confusion Matrix</h3>
{"".join(f"<p><code>{html.escape(expected)}</code> -> {html.escape(', '.join(f'{actual}: {count}' for actual, count in sorted(actuals.items())))}</p>" for expected, actuals in sorted((agent.get("confusion_matrix") or {}).items())) or "<div class='empty'>No agent confusion matrix data.</div>"}
</section>

<section class="panel">
<h2>Description Overlap</h2>
{_explanation_box("How to read score and shared terms", "Score 是两个 Skill description 的 token Jaccard 相似度：共同词数量 / 合并后的唯一词数量。Shared terms 是共同词示例。高 score 不是错误，但表示 description 可能覆盖相近场景，需要检查边界或补充负例。")}
{_table(["Left", "Right", "Score", "Shared terms"], desc_rows)}
</section>

<section class="panel">
<h2>Eval Case Overlap</h2>
{_explanation_box("How to read this table", "该表比较不同 Skill 的 user_input。高 score 表示两个 Skill 的测试样例很像，可能是合理关联，也可能是功能重复或 expected_skill 边界不清。Inputs 中斜杠左右分别是两个相似 case。")}
{_table(["Left Skill", "Left Case", "Right Skill", "Right Case", "Score", "Inputs"], case_rows)}
</section>
</main>
</body>
</html>
"""


def write_report(report_dir: Path, root: Path) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    data = build_report_data(report_dir, root)
    (report_dir / "summary.md").write_text(render_markdown(data), encoding="utf-8")
    (report_dir / "summary.html").write_text(render_html(data), encoding="utf-8")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Skill eval summary reports.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--report-dir", required=True, help="Report directory containing raw/ results.")
    args = parser.parse_args(argv)
    write_report(Path(args.report_dir).resolve(), Path(args.root).resolve())
    print(f"Wrote {Path(args.report_dir).resolve() / 'summary.md'}")
    print(f"Wrote {Path(args.report_dir).resolve() / 'summary.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
