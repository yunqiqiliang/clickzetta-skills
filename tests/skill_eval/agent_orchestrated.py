"""Summary helpers for agent-orchestrated skill eval results."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def summarize_agent_eval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    trigger_rows = [row for row in rows if row.get("mode") == "trigger"]
    should_call = [row for row in trigger_rows if row.get("case_type") == "should_call"]
    should_not = [row for row in trigger_rows if row.get("case_type") == "should_not_call"]
    with_rows = [row for row in rows if row.get("mode") == "with_skill"]
    baseline_rows = [row for row in rows if row.get("mode") == "baseline"]

    trigger_recall = _pass_rate(should_call)
    negative_pass_rate = _pass_rate(should_not)
    with_rate = _pass_rate(with_rows)
    baseline_rate = _pass_rate(baseline_rows)

    confusion: dict[str, dict[str, int]] = {}
    for row in should_call:
        expected = row.get("expected_skill") or row.get("skill") or "<unknown>"
        selected = row.get("selected_skills") or ["<none>"]
        confusion.setdefault(str(expected), {})
        for actual in selected:
            actual_text = str(actual)
            confusion[str(expected)][actual_text] = confusion[str(expected)].get(actual_text, 0) + 1

    by_case: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in with_rows + baseline_rows:
        key = (str(row.get("skill") or ""), str(row.get("case_id") or ""))
        by_case[key][str(row.get("mode"))] = row

    classification_counts: dict[str, int] = {}
    ab_pairs: list[dict[str, Any]] = []
    for (skill, case_id), modes in sorted(by_case.items()):
        if "with_skill" not in modes or "baseline" not in modes:
            continue
        with_pass = bool(modes["with_skill"].get("passed"))
        baseline_pass = bool(modes["baseline"].get("passed"))
        classification = (
            "high_value" if with_pass and not baseline_pass else
            "neutral" if with_pass and baseline_pass else
            "regression" if baseline_pass and not with_pass else
            "both_fail"
        )
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
        ab_pairs.append(
            {
                "skill": skill,
                "case_id": case_id,
                "with_passed": with_pass,
                "baseline_passed": baseline_pass,
                "uplift": int(with_pass) - int(baseline_pass),
                "classification": classification,
                "with_evidence": modes["with_skill"].get("evidence") or modes["with_skill"].get("failure_reason") or "",
                "baseline_evidence": modes["baseline"].get("evidence") or modes["baseline"].get("failure_reason") or "",
            }
        )

    average_uplift = None
    if with_rate is not None and baseline_rate is not None:
        average_uplift = with_rate - baseline_rate

    return {
        "row_count": len(rows),
        "trigger_case_count": len(trigger_rows),
        "should_call_count": len(should_call),
        "should_not_call_count": len(should_not),
        "trigger_recall": trigger_recall,
        "negative_pass_rate": negative_pass_rate,
        "failed_trigger_cases": [row for row in trigger_rows if not row.get("passed")],
        "confusion_matrix": confusion,
        "ab_case_count": len(ab_pairs),
        "with_skill_pass_rate": with_rate,
        "baseline_pass_rate": baseline_rate,
        "average_uplift": average_uplift,
        "classification_counts": classification_counts,
        "ab_pairs": ab_pairs,
        "regression_cases": [row for row in ab_pairs if row["classification"] == "regression"],
        "both_fail_cases": [row for row in ab_pairs if row["classification"] == "both_fail"],
    }


def _pass_rate(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    return sum(bool(row.get("passed")) for row in rows) / len(rows)

