"""Lightweight overlap analysis for skill boundary checks."""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Any

from .core import iter_skill_dirs, load_all_eval_cases, load_skill, normalize_description


TOKEN_RE = re.compile(r"[a-zA-Z0-9_+-]+|[\u4e00-\u9fff]")


def _tokens(text: str) -> set[str]:
    toks = [t.lower() for t in TOKEN_RE.findall(text)]
    grams = {"".join(toks[i:i + 2]) for i in range(len(toks) - 1) if len(toks[i]) == 1 and len(toks[i + 1]) == 1}
    return set(toks) | grams


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def analyze_description_overlap(root: Path, threshold: float = 0.18) -> list[dict[str, Any]]:
    rows = []
    descs: dict[str, str] = {}
    token_sets: dict[str, set[str]] = {}
    for skill_dir in iter_skill_dirs(root):
        skill, issue = load_skill(skill_dir)
        if issue or not skill:
            continue
        desc = normalize_description(skill.frontmatter.get("description"))
        descs[skill_dir.name] = desc
        token_sets[skill_dir.name] = _tokens(desc)
    for left, right in itertools.combinations(sorted(token_sets), 2):
        score = _jaccard(token_sets[left], token_sets[right])
        if score >= threshold:
            shared = sorted(token_sets[left] & token_sets[right])
            rows.append(
                {
                    "left": left,
                    "right": right,
                    "score": round(score, 4),
                    "shared_terms": shared[:20],
                    "left_description": descs[left][:240],
                    "right_description": descs[right][:240],
                }
            )
    return sorted(rows, key=lambda x: x["score"], reverse=True)


def analyze_case_overlap(root: Path, threshold: float = 0.34) -> list[dict[str, Any]]:
    cases, _ = load_all_eval_cases(root)
    positive = [c for c in cases if c.case_type == "should_call"]
    token_sets = {f"{c.skill_name}:{c.case_id}": _tokens(c.user_input) for c in positive}
    by_key = {f"{c.skill_name}:{c.case_id}": c for c in positive}
    rows = []
    for left, right in itertools.combinations(sorted(token_sets), 2):
        left_case = by_key[left]
        right_case = by_key[right]
        if left_case.skill_name == right_case.skill_name:
            continue
        score = _jaccard(token_sets[left], token_sets[right])
        if score >= threshold:
            rows.append(
                {
                    "left_skill": left_case.skill_name,
                    "left_case_id": left_case.case_id,
                    "left_input": left_case.user_input,
                    "right_skill": right_case.skill_name,
                    "right_case_id": right_case.case_id,
                    "right_input": right_case.user_input,
                    "score": round(score, 4),
                }
            )
    return sorted(rows, key=lambda x: x["score"], reverse=True)


def analyze_overlap(root: Path) -> dict[str, Any]:
    return {
        "description_overlap": analyze_description_overlap(root),
        "case_overlap": analyze_case_overlap(root),
    }

