"""Shared utilities for ClickZetta skill evaluation.

The modules in this package intentionally avoid pytest imports so they can be
used both from tests and from CLI entry points.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class SkillInfo:
    name: str
    path: Path
    skill_md: Path
    frontmatter: dict[str, Any]
    body: str


@dataclass(frozen=True)
class EvalCase:
    skill_name: str
    case_id: str
    case_type: str
    user_input: str
    expected_skill: str | None = None
    forbidden_skill: str | None = None
    expected_output_contains: list[str] = field(default_factory=list)
    expected_output_not_contains: list[str] = field(default_factory=list)
    assertions: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    path: str
    skill: str | None = None


def repo_root_from(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path).resolve()
    return Path(__file__).resolve().parents[2]


def iter_skill_dirs(root: Path) -> list[Path]:
    return sorted(
        p for p in root.iterdir()
        if p.is_dir() and p.name.startswith("clickzetta-") and (p / "SKILL.md").exists()
    )


def load_jsonl(path: Path) -> list[tuple[int, dict[str, Any] | Exception]]:
    rows: list[tuple[int, dict[str, Any] | Exception]] = []
    if not path.exists():
        return rows
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append((line_no, json.loads(line)))
        except json.JSONDecodeError as exc:
            rows.append((line_no, exc))
    return rows


def normalize_description(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_frontmatter_text(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, text, "SKILL.md must start with YAML frontmatter"
    raw = match.group(1)
    body = text[match.end():]
    try:
        import yaml
    except ModuleNotFoundError:
        return None, body, "PyYAML is required to parse SKILL.md frontmatter"
    try:
        parsed = yaml.safe_load(raw)
    except Exception as exc:  # pragma: no cover - exact PyYAML type may vary
        return None, body, f"Invalid YAML frontmatter: {exc}"
    if not isinstance(parsed, dict):
        return None, body, "Frontmatter must be a YAML mapping"
    return parsed, body, None


def load_skill(skill_dir: Path) -> tuple[SkillInfo | None, ValidationIssue | None]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None, ValidationIssue(
            "error", "missing-skill-md", "SKILL.md not found", str(skill_md), skill_dir.name
        )
    text = skill_md.read_text(encoding="utf-8")
    frontmatter, body, error = parse_frontmatter_text(text)
    if error:
        return None, ValidationIssue("error", "bad-frontmatter", error, str(skill_md), skill_dir.name)
    name = str(frontmatter.get("name", "")).strip()
    return SkillInfo(name=name, path=skill_dir, skill_md=skill_md, frontmatter=frontmatter, body=body), None


def load_eval_cases(skill_dir: Path) -> tuple[list[EvalCase], list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    path = skill_dir / "eval_cases.jsonl"
    cases: list[EvalCase] = []
    seen: set[str] = set()
    if not path.exists():
        issues.append(
            ValidationIssue(
                "warning", "missing-eval-cases", "eval_cases.jsonl not found", str(path), skill_dir.name
            )
        )
        return cases, issues

    for line_no, row in load_jsonl(path):
        loc = f"{path}:{line_no}"
        if isinstance(row, Exception):
            issues.append(ValidationIssue("error", "bad-eval-json", str(row), loc, skill_dir.name))
            continue
        case_id = str(row.get("case_id", "")).strip()
        if not case_id:
            issues.append(ValidationIssue("error", "missing-case-id", "case_id is required", loc, skill_dir.name))
            continue
        if case_id in seen:
            issues.append(ValidationIssue("error", "duplicate-case-id", f"duplicate case_id {case_id}", loc, skill_dir.name))
        seen.add(case_id)

        case_type = str(row.get("type", "")).strip()
        user_input = str(row.get("user_input", "")).strip()
        if case_type not in {"should_call", "should_not_call"}:
            issues.append(ValidationIssue("error", "bad-case-type", f"unsupported type {case_type!r}", loc, skill_dir.name))
        if not user_input:
            issues.append(ValidationIssue("error", "missing-user-input", "user_input is required", loc, skill_dir.name))

        expected_skill = row.get("expected_skill")
        forbidden_skill = row.get("forbidden_skill")
        if case_type == "should_call" and not expected_skill:
            issues.append(ValidationIssue("error", "missing-expected-skill", "should_call requires expected_skill", loc, skill_dir.name))
        if case_type == "should_not_call" and not forbidden_skill:
            issues.append(ValidationIssue("error", "missing-forbidden-skill", "should_not_call requires forbidden_skill", loc, skill_dir.name))
        if expected_skill and expected_skill != skill_dir.name:
            issues.append(
                ValidationIssue(
                    "warning",
                    "cross-skill-expected",
                    f"expected_skill {expected_skill!r} differs from folder {skill_dir.name!r}",
                    loc,
                    skill_dir.name,
                )
            )
        if forbidden_skill and forbidden_skill != skill_dir.name:
            issues.append(
                ValidationIssue(
                    "warning",
                    "cross-skill-forbidden",
                    f"forbidden_skill {forbidden_skill!r} differs from folder {skill_dir.name!r}",
                    loc,
                    skill_dir.name,
                )
            )

        contains = row.get("expected_output_contains") or []
        not_contains = row.get("expected_output_not_contains") or []
        assertions = row.get("assertions") or []
        if isinstance(contains, str):
            contains = [contains]
        if isinstance(not_contains, str):
            not_contains = [not_contains]
        if not isinstance(assertions, list):
            issues.append(ValidationIssue("error", "bad-assertions", "assertions must be a list", loc, skill_dir.name))
            assertions = []

        cases.append(
            EvalCase(
                skill_name=skill_dir.name,
                case_id=case_id,
                case_type=case_type,
                user_input=user_input,
                expected_skill=str(expected_skill) if expected_skill else None,
                forbidden_skill=str(forbidden_skill) if forbidden_skill else None,
                expected_output_contains=[str(x) for x in contains],
                expected_output_not_contains=[str(x) for x in not_contains],
                assertions=assertions,
                raw=row,
            )
        )
    if not any(c.case_type == "should_call" for c in cases):
        issues.append(ValidationIssue("warning", "no-positive-cases", "no should_call cases found", str(path), skill_dir.name))
    if not any(c.case_type == "should_not_call" for c in cases):
        issues.append(ValidationIssue("warning", "no-negative-cases", "no should_not_call cases found", str(path), skill_dir.name))
    return cases, issues


def load_all_eval_cases(root: Path, skill_name: str | None = None) -> tuple[list[EvalCase], list[ValidationIssue]]:
    cases: list[EvalCase] = []
    issues: list[ValidationIssue] = []
    for skill_dir in iter_skill_dirs(root):
        if skill_name and skill_dir.name != skill_name:
            continue
        skill_cases, skill_issues = load_eval_cases(skill_dir)
        cases.extend(skill_cases)
        issues.extend(skill_issues)
    return cases, issues

