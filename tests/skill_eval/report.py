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


def _render_executive_summary(data: dict[str, Any]) -> list[str]:
    static_errors = [x for x in data["static"] if x["severity"] == "error"]
    static_warnings = [x for x in data["static"] if x["severity"] == "warning"]
    trigger = data["trigger_summary"]
    ab = data["ab_summary"]
    agent = data["agent_summary"]

    # 整体健康判断
    has_agent = bool(data.get("agent"))
    trigger_recall = agent.get("trigger_recall") if has_agent else trigger.get("trigger_recall")
    uplift = agent.get("average_uplift") if has_agent else ab.get("average_uplift")

    if static_errors:
        health = "❌ 存在阻塞性静态错误，需优先修复后再信任 eval 结果。"
    elif trigger_recall is not None and trigger_recall < 0.7:
        health = "⚠️ 触发准确率偏低，建议检查 skill description 和 eval case。"
    elif trigger_recall is not None and trigger_recall >= 0.9 and (uplift is None or uplift >= 0):
        health = "✅ 整体健康，无阻塞问题，触发准确率良好。"
    else:
        health = "⚠️ 部分指标需关注，详见下方各节。"

    lines = ["## 总结", "", health, ""]

    # 静态校验
    no_neg = sum(1 for x in static_warnings if x.get("code") == "no-negative-cases")
    idx_mismatch = sum(1 for x in static_warnings if x.get("code") == "index-description-mismatch")
    missing_eval = sum(1 for x in static_warnings if x.get("code") == "missing-eval-cases")
    lines.append(f"**静态校验**：{len(static_errors)} 个 error，{len(static_warnings)} 个 warning。")
    if not static_errors:
        lines.append("无阻塞问题。")
    else:
        lines.append(f"存在 {len(static_errors)} 个阻塞性错误，需优先修复。")
    if static_warnings:
        detail_parts = []
        if no_neg:
            detail_parts.append(f"`no-negative-cases` {no_neg} 个（缺少负例）")
        if idx_mismatch:
            detail_parts.append(f"`index-description-mismatch` {idx_mismatch} 个（index 元数据未同步）")
        if missing_eval:
            detail_parts.append(f"`missing-eval-cases` {missing_eval} 个（缺少 eval_cases.jsonl）")
        other = len(static_warnings) - no_neg - idx_mismatch - missing_eval
        if other > 0:
            detail_parts.append(f"其他 {other} 个")
        if detail_parts:
            lines.append("Warning 分布：" + "，".join(detail_parts) + "。")
    lines.append("")

    # 触发准确率
    if has_agent and agent.get("trigger_case_count", 0) > 0:
        recall = agent.get("trigger_recall")
        neg = agent.get("negative_pass_rate")
        failed = agent.get("failed_trigger_cases") or []
        lines.append(
            f"**触发准确率**（Agent eval）：{_pct(recall)}（{agent.get('trigger_case_count', 0)} 个 trigger case，"
            f"{len(failed)} 个失败）。负例通过率：{_pct(neg)}。"
        )
        if failed:
            for row in failed[:3]:
                reason = row.get("failure_reason") or row.get("evidence") or ""
                lines.append(f"  - `{row.get('skill')}#{row.get('case_id')}`：{reason[:120]}")
    elif trigger.get("case_count", 0) > 0:
        lines.append(
            f"**触发准确率**（脚本 eval）：{_pct(trigger.get('trigger_recall'))}，"
            f"负例通过率：{_pct(trigger.get('negative_pass_rate'))}。"
        )
    else:
        lines.append("**触发准确率**：脚本驱动 trigger eval 未运行，Agent eval 也无 trigger 数据。")
    lines.append("")

    # A/B 增益
    if has_agent and agent.get("ab_case_count", 0) > 0:
        clf = agent.get("classification_counts") or {}
        high = clf.get("high_value", 0)
        neutral = clf.get("neutral", 0)
        regression = clf.get("regression", 0)
        both_fail = clf.get("both_fail", 0)
        lines.append(
            f"**A/B 增益**（Agent eval）：with-skill 通过率 {_pct(agent.get('with_skill_pass_rate'))}，"
            f"baseline {_pct(agent.get('baseline_pass_rate'))}，平均 uplift **{_pct(agent.get('average_uplift'))}**。"
        )
        lines.append(
            f"分类：high_value {high}，neutral {neutral}，regression {regression}，both_fail {both_fail}。"
        )
        if regression > 0:
            lines.append(f"  ⚠️ {regression} 个 regression case（使用 skill 后反而变差），建议检查对应 skill 内容。")
    elif ab.get("case_count", 0) > 0:
        lines.append(
            f"**A/B 增益**（脚本 eval）：with-skill {_pct(ab.get('with_skill_pass_rate'))}，"
            f"baseline {_pct(ab.get('baseline_pass_rate'))}，uplift {_pct(ab.get('average_uplift'))}。"
        )
    else:
        lines.append("**A/B 增益**：A/B eval 未运行，无对比数据。")
    lines.append("")

    # Overlap
    desc_overlap = data["overlap"]["description_overlap"]
    if desc_overlap:
        top = desc_overlap[0]
        lines.append(
            f"**Overlap 分析**：发现 {len(desc_overlap)} 对 description 重叠，"
            f"最高为 `{top['left']}` ↔ `{top['right']}`（score={top['score']}）。"
            "高重叠不一定是问题，但建议检查边界或补充负例。"
        )
    else:
        lines.append("**Overlap 分析**：未发现显著 description 重叠。")
    lines.append("")

    return lines


def render_markdown(data: dict[str, Any]) -> str:
    static_errors = [x for x in data["static"] if x["severity"] == "error"]
    static_warnings = [x for x in data["static"] if x["severity"] == "warning"]
    trigger = data["trigger_summary"]
    ab = data["ab_summary"]
    agent = data["agent_summary"]
    has_agent = bool(data.get("agent"))
    model_eval_note = (
        "本次报告包含 Agent 编排 eval 原始结果（`raw/agent_eval_results.jsonl`）。"
        if _has_model_eval_data(data)
        else "本次报告未包含模型 eval 原始结果，仅展示静态校验和 overlap 分析。如需运行 Agent eval，请参考 `tests/agent_eval/RUNBOOK.md`。"
    )
    lines = [
        "# ClickZetta Skills Eval 报告",
        "",
    ]
    # 全局总结放在最前面
    lines.extend(_render_executive_summary(data))
    lines.extend([
        "## 报告结构说明",
        "",
        "本报告包含五个评测层：",
        "",
        "- **静态校验**：检查 `SKILL.md`、frontmatter、`.well-known/skills/index.json`、`eval_cases.jsonl` 是否符合发布规范。",
        "- **触发 eval**（脚本驱动）：通过脚本向 agent 喂 prompt，检测 skill 触发准确率。",
        "- **A/B uplift eval**（脚本驱动）：对比 with_skill 和 baseline 的回答质量。",
        "- **Agent 编排 eval**：由 Claude/Codex 子 agent 并发执行 trigger、with_skill、baseline 三类任务，结果写入 `raw/agent_eval_results.jsonl`。**本次 eval 使用此层。**",
        "- **Overlap 分析**：扫描 description 和 eval prompt 的相似度，发现 skill 边界重叠。",
        "",
        model_eval_note,
        "",
        "## 数据概览",
        "",
        f"- 静态校验：{len(static_errors)} 个 error，{len(static_warnings)} 个 warning",
        f"- 脚本 trigger cases：{trigger.get('case_count', 0)}",
        f"- 脚本 trigger recall：{_pct(trigger.get('trigger_recall'))}",
        f"- 脚本 A/B cases：{ab.get('case_count', 0)}",
        f"- 脚本 A/B uplift：{_pct(ab.get('average_uplift')) if ab.get('case_count') else 'n/a'}",
        f"- Agent eval 行数：{agent.get('row_count', 0)}",
        f"- Agent trigger recall：{_pct(agent.get('trigger_recall'))}",
        f"- Agent A/B cases：{agent.get('ab_case_count', 0)}",
        f"- Agent 平均 uplift：{_pct(agent.get('average_uplift')) if agent.get('ab_case_count') else 'n/a'}",
        "",
        "## 字段说明",
        "",
        "- `severity`：`error` 阻塞静态校验；`warning` 表示质量债或覆盖不足。",
        "- `code`：问题类别，便于分组和自动化处理。",
        "- `skill`：受影响的 skill 目录名。",
        "- `score`：overlap 相似度，0 到 1，越高表示两个文本共享词越多。",
        "- `shared_terms`：两个描述或 eval prompt 共同出现的词。",
        "- `triggered_skills`：从 agent/tool trace 中检测到的实际触发 skill。",
        "- `selected_skills`：Agent 编排 eval 中子 agent 选择的 skill。",
        "- `worker_id`：产生该行结果的子 agent 标识。",
        "- `uplift`：with-skill 结果减去 baseline 结果（A/B 对比）。",
        "",
        "## 静态校验问题",
        "",
        "静态校验检查仓库是否可作为完整的 skill 发布制品。error 需优先修复；warning 通常表示缺少负例、index 元数据未同步或 description 偏长。",
        "",
    ])
    if not data["static"]:
        lines.append("未发现静态问题。")
    else:
        for issue in data["static"][:200]:
            lines.append(f"- **{issue['severity']}** `{issue['code']}` `{issue.get('skill') or '-'}`: {issue['message']} ({issue['path']})")
    lines.extend(["", "## 触发失败（脚本 eval）", ""])
    lines.append("本节展示脚本驱动 trigger eval 中触发失败的 case（期望触发但未触发，或不该触发却触发）。")
    lines.append("")
    failed_trigger = trigger.get("failed_cases", [])
    if not failed_trigger:
        if trigger.get("case_count", 0) == 0:
            if has_agent:
                lines.append("脚本驱动 trigger eval 未运行（trigger cases = 0）。")
                lines.append("→ Agent eval 的触发失败请查看下方 **Agent 编排 eval → Agent 触发失败** 节。")
            else:
                lines.append("脚本驱动 trigger eval 未运行，且无 Agent eval 数据。")
        else:
            lines.append("无触发失败记录。")
    else:
        for row in failed_trigger[:100]:
            lines.append(f"- `{row['skill']}#{row['case_id']}` {row['type']}: triggered={row.get('triggered_skills')} input={row['user_input']}")
    lines.extend(["", "## A/B 分类（脚本 eval）", ""])
    lines.append("A/B 分类说明使用 skill 是否改善了模型回答质量：")
    lines.append("")
    lines.append("- `high_value`：with-skill 通过，baseline 失败——skill 有明显帮助。")
    lines.append("- `neutral`：两边都通过——skill 不是必须的，但也无害。")
    lines.append("- `regression`：baseline 通过，with-skill 失败——使用 skill 反而变差，需检查。")
    lines.append("- `both_fail`：两边都失败——skill 内容或 eval case 需要改进。")
    lines.append("")
    ab_clf = ab.get("classification_counts") or {}
    if ab_clf:
        for key, value in sorted(ab_clf.items()):
            lines.append(f"- `{key}`: {value}")
    else:
        if has_agent:
            lines.append("脚本驱动 A/B eval 未运行（A/B cases = 0）。")
            lines.append("→ Agent eval 的 A/B 分类请查看下方 **Agent 编排 eval → Agent A/B 分类** 节。")
        else:
            lines.append("脚本驱动 A/B eval 未运行，且无 Agent eval 数据。")
    lines.extend(["", "## Skill 混淆矩阵（脚本 eval）", ""])
    lines.append("混淆矩阵来自脚本驱动 trigger eval。每行含义：期望触发的 skill → 实际检测到的 skill。非对角线条目是 skill 混淆的主要信号。")
    lines.append("")
    confusion = trigger.get("confusion_matrix") or {}
    if not confusion:
        if has_agent:
            lines.append("脚本驱动 trigger eval 未运行，无混淆矩阵数据。")
            lines.append("→ Agent eval 的混淆矩阵请查看下方 **Agent 编排 eval → Agent 混淆矩阵** 节。")
        else:
            lines.append("脚本驱动 trigger eval 未运行，无混淆矩阵数据。")
    else:
        for expected, actuals in sorted(confusion.items()):
            rendered = ", ".join(f"{actual}: {count}" for actual, count in sorted(actuals.items()))
            lines.append(f"- `{expected}` -> {rendered}")
    lines.extend(["", "## Agent 编排 eval", ""])
    lines.append("本层由 Claude/Codex 按 `tests/agent_eval/RUNBOOK.md` 并发调度子 agent，结果写入 `raw/agent_eval_results.jsonl`。**当前 eval 主要使用此层。**")
    lines.append("")
    if not data.get("agent"):
        lines.append("未记录 Agent 编排 eval 数据。")
    else:
        lines.append(f"- 总行数：{agent.get('row_count', 0)}")
        lines.append(f"- Trigger cases：{agent.get('trigger_case_count', 0)}")
        lines.append(f"- Trigger recall：{_pct(agent.get('trigger_recall'))}")
        lines.append(f"- 负例通过率：{_pct(agent.get('negative_pass_rate'))}")
        lines.append(f"- A/B pairs：{agent.get('ab_case_count', 0)}")
        lines.append(f"- With-skill 通过率：{_pct(agent.get('with_skill_pass_rate'))}")
        lines.append(f"- Baseline 通过率：{_pct(agent.get('baseline_pass_rate'))}")
        lines.append(f"- 平均 uplift：{_pct(agent.get('average_uplift'))}")
        lines.append("")
        lines.append("### Agent A/B 分类")
        lines.append("")
        for key, value in sorted((agent.get("classification_counts") or {}).items()):
            lines.append(f"- `{key}`: {value}")
        lines.append("")
        lines.append("### Agent 混淆矩阵")
        lines.append("")
        agent_confusion = agent.get("confusion_matrix") or {}
        if not agent_confusion:
            lines.append("无 Agent 混淆矩阵数据。")
        else:
            for expected, actuals in sorted(agent_confusion.items()):
                rendered = ", ".join(f"{actual}: {count}" for actual, count in sorted(actuals.items()))
                lines.append(f"- `{expected}` -> {rendered}")
        failed_agent = agent.get("failed_trigger_cases") or []
        if failed_agent:
            lines.append("")
            lines.append("### Agent 触发失败")
            lines.append("")
            for row in failed_agent[:50]:
                lines.append(
                    f"- `{row.get('skill')}#{row.get('case_id')}` {row.get('case_type')}: "
                    f"selected={row.get('selected_skills')} reason={row.get('failure_reason') or row.get('evidence') or ''}"
                )
    lines.extend(["", "## Overlap 分析", ""])
    lines.append("Overlap 分析是启发式的，高分不代表一定有问题，但是检查 skill 边界、补充负例的参考信号。")
    lines.append("")
    desc_overlap = data["overlap"]["description_overlap"][:30]
    case_overlap = data["overlap"]["case_overlap"][:30]
    lines.append("### Description 重叠")
    lines.append("")
    lines.append("比较各 skill 的 frontmatter description。`score` 是 token Jaccard 相似度：共同词数 / 两个描述合并后的唯一词数。")
    lines.append("")
    if not desc_overlap:
        lines.append("未发现高 description 重叠。")
    else:
        for row in desc_overlap:
            lines.append(f"- `{row['left']}` ↔ `{row['right']}` score={row['score']} shared={', '.join(row['shared_terms'][:8])}")
    lines.append("")
    lines.append("### Eval case 重叠")
    lines.append("")
    lines.append("比较不同 skill 的 user_input。高分表示两个 skill 的测试样例很像，可能需要检查功能边界或补充负例。")
    lines.append("")
    if not case_overlap:
        lines.append("未发现高跨 skill eval case 重叠。")
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
    # 生成 HTML 总结段落
    has_agent_html = bool(data.get("agent"))
    card_html = "".join(
        f"<section class='card {_status_class(v)}'><div>{html.escape(k)}</div><strong>{html.escape(str(v))}</strong></section>"
        for k, v in cards
    )
    model_eval_note = (
        "本次报告包含 Agent 编排 eval 原始结果（`raw/agent_eval_results.jsonl`）。"
        if _has_model_eval_data(data)
        else "本次报告未包含模型 eval 原始结果，仅展示静态校验和 overlap 分析。如需运行 Agent eval，请参考 `tests/agent_eval/RUNBOOK.md`。"
    )
    static_explanation = _interpret_static(len(static_errors), len(static_warnings))
    trigger_recall_meaning = _interpret_rate(trigger.get("trigger_recall"))
    negative_meaning = _interpret_rate(trigger.get("negative_pass_rate"))
    average_uplift = ab.get("average_uplift") if ab.get("case_count") else None
    summary_lines = _render_executive_summary(data)
    summary_html = "".join(
        f"<p>{html.escape(line)}</p>" if line and not line.startswith("#") and not line.startswith("**") else
        (f"<h3>{html.escape(line.lstrip('#').strip())}</h3>" if line.startswith("#") else
         f"<p><strong>{html.escape(line.strip('*'))}</strong></p>" if line.startswith("**") else "")
        for line in summary_lines if line.strip()
    )
    # 三处空 section 的重定向提示
    trigger_empty_msg = (
        "<div class='empty'>脚本驱动 trigger eval 未运行（trigger cases = 0）。"
        "→ Agent eval 的触发失败请查看下方 <a href='#agent-eval'>Agent 编排 eval → Agent 触发失败</a>。</div>"
        if not trigger_rows and trigger.get("case_count", 0) == 0 and has_agent_html
        else "<div class='empty'>无触发失败记录。</div>"
    )
    ab_empty_msg = (
        "<div class='empty'>脚本驱动 A/B eval 未运行（A/B cases = 0）。"
        "→ Agent eval 的 A/B 分类请查看下方 <a href='#agent-eval'>Agent 编排 eval → Agent A/B 分类</a>。</div>"
        if not (ab.get("classification_counts") or {}) and has_agent_html
        else "<div class='empty'>无 A/B 分类数据。</div>"
    )
    confusion_empty_msg = (
        "<div class='empty'>脚本驱动 trigger eval 未运行，无混淆矩阵数据。"
        "→ Agent eval 的混淆矩阵请查看下方 <a href='#agent-eval'>Agent 编排 eval → Agent 混淆矩阵</a>。</div>"
        if not (trigger.get("confusion_matrix") or {}) and has_agent_html
        else "<div class='empty'>无混淆矩阵数据。</div>"
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClickZetta Skills Eval 报告</title>
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
.summary {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin: 16px 0; }}
.summary h3 {{ color: #166534; margin: 12px 0 4px; }}
.dictionary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; }}
.term {{ background: #fbfcfe; border: 1px solid #dbe3ef; border-radius: 8px; padding: 11px; }}
.term strong {{ display: block; margin-bottom: 4px; }}
table {{ width: 100%; border-collapse: collapse; background: white; margin: 8px 0 28px; font-size: 13px; }}
th, td {{ border: 1px solid #dbe3ef; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}
.empty {{ color: #64748b; background: #fbfcfe; border: 1px dashed #cbd5e1; padding: 12px; border-radius: 8px; }}
.empty a {{ color: #2563eb; }}
ul {{ margin-top: 8px; }}
</style>
</head>
<body>
<main>
<h1>ClickZetta Skills Eval 报告</h1>
<p class="lead">评估 ClickZetta Skill 仓库的结构质量、触发准确率、A/B 增益和 Skill 边界重叠。</p>
<div class="grid">{card_html}</div>

<section class="panel summary">
<h2>总结</h2>
{summary_html}
</section>

<section class="panel">
<h2>报告结构说明</h2>
<p>{html.escape(model_eval_note)}</p>
<div class="dictionary">
<div class="term"><strong>静态校验</strong>检查 <code>SKILL.md</code>、frontmatter、index 和 eval case 是否是可发布的 Skill 制品。当前解读：{html.escape(static_explanation)}</div>
<div class="term"><strong>触发准确率（脚本）</strong><code>should_call</code> 中成功触发期望 Skill 的比例。当前解读：{html.escape(trigger_recall_meaning)}</div>
<div class="term"><strong>负例通过率（脚本）</strong><code>should_not_call</code> 中成功避免 forbidden Skill 的比例。当前解读：{html.escape(negative_meaning)}</div>
<div class="term"><strong>平均 uplift（脚本）</strong>with-skill 通过率减去 baseline 通过率。当前值：{html.escape(_pct(average_uplift))}。</div>
<div class="term"><strong>Agent eval</strong>Claude/Codex 按 <code>tests/agent_eval/RUNBOOK.md</code> 并发运行 case 后写入 <code>raw/agent_eval_results.jsonl</code>。当前 Agent rows：{html.escape(str(agent.get("row_count", 0)))}。</div>
<div class="term"><strong>Score</strong>Overlap 相似度，范围 0 到 1。越高表示两个文本共享词越多，越需要检查 Skill 边界。</div>
<div class="term"><strong>Shared terms</strong>两个描述或两个 eval prompt 共同出现的词，是 score 的主要来源。</div>
</div>
</section>

<section class="panel">
<h2>指标说明</h2>
<ul>
<li><strong>Static errors</strong>：阻塞性结构问题，应优先修复。当前 pytest 只会因 error 失败。</li>
<li><strong>Static warnings</strong>：质量债或覆盖不足，例如缺少负例、index 元数据不同步、description 偏长。</li>
<li><strong>Trigger cases</strong>：参与脚本触发测试的 case 数量。为 0 表示脚本驱动 eval 未运行；Agent eval 数据见下方。</li>
<li><strong>A/B cases</strong>：参与 with-skill vs baseline 对比的 case 数量。为 0 表示脚本驱动 eval 未运行；Agent eval 数据见下方。</li>
<li><strong>Agent rows</strong>：由 Claude/Codex 子 agent 直接生成的结构化评测行，来源是 <code>raw/agent_eval_results.jsonl</code>。</li>
<li><strong>Description overlap</strong>：比较 Skill frontmatter description，用于发现触发描述是否重叠。</li>
<li><strong>Eval case overlap</strong>：比较不同 Skill 的用户样例，用于发现测试样例和功能范围是否重叠。</li>
</ul>
</section>

<section class="panel">
<h2>静态校验问题</h2>
{_explanation_box("说明", "每一行都是一个静态校验发现。Severity 为 error 表示阻塞问题；warning 表示不阻塞当前测试但建议治理。Code 是问题类别，Skill 是受影响的 skill，Message 是具体解释。")}
{_table(["Severity", "Code", "Skill", "Message", "Path"], static_rows)}
</section>

<section class="panel">
<h2>触发失败（脚本 eval）</h2>
{_explanation_box("说明", "本节仅在运行脚本驱动 trigger eval 后有内容。展示应该触发但没触发、或不该触发却触发的 case。若 Trigger cases = 0，表示脚本 eval 未运行，请查看下方 Agent 编排 eval 节。")}
{_table(["Skill", "Case", "Type", "Triggered", "Input"], trigger_rows) if trigger_rows else trigger_empty_msg}
</section>

<section class="panel">
<h2>A/B 分类（脚本 eval）</h2>
{_explanation_box("分类说明", "high_value：Skill 帮助明显；neutral：两边都能答对；regression：使用 Skill 反而变差；both_fail：Skill 和 baseline 都没通过。若 A/B cases = 0，表示脚本 eval 未运行，请查看下方 Agent 编排 eval 节。")}
{_table(["Classification", "Count"], [[k, v] for k, v in sorted((ab.get("classification_counts") or {}).items())]) if (ab.get("classification_counts") or {}) else ab_empty_msg}
</section>

<section class="panel">
<h2>Skill 混淆矩阵（脚本 eval）</h2>
{_explanation_box("说明", "混淆矩阵来自脚本驱动 trigger eval。每一行表示 expected skill → actual detected skill。对角线是正确触发；非对角线表示 Skill 之间可能混淆。若 Trigger cases = 0，表示脚本 eval 未运行，请查看下方 Agent 编排 eval 节。")}
{"".join(f"<p><code>{html.escape(expected)}</code> -> {html.escape(', '.join(f'{actual}: {count}' for actual, count in sorted(actuals.items())))}</p>" for expected, actuals in sorted((trigger.get("confusion_matrix") or {}).items())) or confusion_empty_msg}
</section>

<section class="panel" id="agent-eval">
<h2>Agent 编排 eval</h2>
{_explanation_box("说明", "本层由 Claude/Codex 按 tests/agent_eval/RUNBOOK.md 并发调度子 agent，让 agent 自己执行 trigger、with_skill、baseline 三类任务并写入 raw/agent_eval_results.jsonl。当前 eval 主要使用此层。")}
<div class="dictionary">
<div class="term"><strong>总行数</strong>{html.escape(str(agent.get("row_count", 0)))}</div>
<div class="term"><strong>Trigger recall</strong>{html.escape(_pct(agent.get("trigger_recall")))}</div>
<div class="term"><strong>负例通过率</strong>{html.escape(_pct(agent.get("negative_pass_rate")))}</div>
<div class="term"><strong>平均 uplift</strong>{html.escape(_pct(agent.get("average_uplift")) if agent.get("ab_case_count") else "n/a")}</div>
</div>
<h3>Agent A/B 分类</h3>
{_table(["Skill", "Case", "Classification", "Uplift", "With evidence", "Baseline evidence"], agent_ab_rows) if agent_ab_rows else "<div class='empty'>无 Agent A/B 数据。</div>"}
<h3>Agent 触发失败</h3>
{_table(["Skill", "Case", "Type", "Selected skills", "Reason"], agent_failed_rows) if agent_failed_rows else "<div class='empty'>无 Agent 触发失败记录。</div>"}
<h3>Agent 混淆矩阵</h3>
{"".join(f"<p><code>{html.escape(expected)}</code> -> {html.escape(', '.join(f'{actual}: {count}' for actual, count in sorted(actuals.items())))}</p>" for expected, actuals in sorted((agent.get("confusion_matrix") or {}).items())) or "<div class='empty'>无 Agent 混淆矩阵数据。</div>"}
</section>

<section class="panel">
<h2>Description 重叠</h2>
{_explanation_box("说明", "Score 是两个 Skill description 的 token Jaccard 相似度：共同词数量 / 合并后的唯一词数量。高 score 不是错误，但表示 description 可能覆盖相近场景，需要检查边界或补充负例。")}
{_table(["Left", "Right", "Score", "Shared terms"], desc_rows)}
</section>

<section class="panel">
<h2>Eval Case 重叠</h2>
{_explanation_box("说明", "比较不同 Skill 的 user_input。高 score 表示两个 Skill 的测试样例很像，可能是合理关联，也可能是功能重复或 expected_skill 边界不清。Inputs 中斜杠左右分别是两个相似 case。")}
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
