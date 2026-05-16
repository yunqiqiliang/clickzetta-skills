"""Static validation for ClickZetta skills."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import (
    SKILL_NAME_RE,
    ValidationIssue,
    iter_skill_dirs,
    load_eval_cases,
    load_skill,
    normalize_description,
)


ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
DESCRIPTION_SOFT_LIMIT = 1024
DESCRIPTION_HARD_LIMIT = 3000


def _issue(severity: str, code: str, message: str, path: Path | str, skill: str | None = None) -> ValidationIssue:
    return ValidationIssue(severity, code, message, str(path), skill)


def _validate_skill_metadata(skill_dir: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    skill, load_issue = load_skill(skill_dir)
    if load_issue:
        return [load_issue]
    assert skill is not None
    fm = skill.frontmatter
    unexpected = set(fm) - ALLOWED_FRONTMATTER_KEYS
    if unexpected:
        issues.append(
            _issue(
                "error",
                "unexpected-frontmatter-key",
                f"Unexpected frontmatter key(s): {', '.join(sorted(unexpected))}",
                skill.skill_md,
                skill_dir.name,
            )
        )
    if "name" not in fm:
        issues.append(_issue("error", "missing-name", "frontmatter.name is required", skill.skill_md, skill_dir.name))
    if "description" not in fm:
        issues.append(_issue("error", "missing-description", "frontmatter.description is required", skill.skill_md, skill_dir.name))

    name = fm.get("name")
    if not isinstance(name, str):
        issues.append(_issue("error", "bad-name-type", "frontmatter.name must be a string", skill.skill_md, skill_dir.name))
    else:
        stripped = name.strip()
        if stripped != skill_dir.name:
            issues.append(
                _issue(
                    "error",
                    "name-folder-mismatch",
                    f"frontmatter.name {stripped!r} must match folder name {skill_dir.name!r}",
                    skill.skill_md,
                    skill_dir.name,
                )
            )
        if not SKILL_NAME_RE.match(stripped):
            issues.append(_issue("error", "bad-name-format", "name must be lowercase kebab-case", skill.skill_md, skill_dir.name))
        if len(stripped) > 64:
            issues.append(_issue("error", "name-too-long", "name must be <= 64 characters", skill.skill_md, skill_dir.name))

    description = fm.get("description")
    if not isinstance(description, str):
        issues.append(_issue("error", "bad-description-type", "frontmatter.description must be a string", skill.skill_md, skill_dir.name))
    else:
        desc = normalize_description(description)
        if not desc:
            issues.append(_issue("error", "empty-description", "description cannot be empty", skill.skill_md, skill_dir.name))
        if "<" in desc or ">" in desc:
            issues.append(_issue("warning", "description-angle-brackets", "description contains angle brackets", skill.skill_md, skill_dir.name))
        if len(desc) > DESCRIPTION_HARD_LIMIT:
            issues.append(
                _issue("error", "description-too-long", f"description is {len(desc)} chars; hard limit is {DESCRIPTION_HARD_LIMIT}", skill.skill_md, skill_dir.name)
            )
        elif len(desc) > DESCRIPTION_SOFT_LIMIT:
            issues.append(
                _issue(
                    "warning",
                    "description-long",
                    f"description is {len(desc)} chars; recommended max is {DESCRIPTION_SOFT_LIMIT}",
                    skill.skill_md,
                    skill_dir.name,
                )
            )
        trigger_markers = ("当用户", "触发", "Use when", "use this skill", "Trigger for", "MUST trigger")
        if not any(marker.lower() in desc.lower() for marker in trigger_markers):
            issues.append(
                _issue(
                    "warning",
                    "description-missing-trigger",
                    "description should include trigger/use conditions because only metadata is loaded initially",
                    skill.skill_md,
                    skill_dir.name,
                )
            )
    return issues


def _validate_index(root: Path, skill_dirs: list[Path]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    index_path = root / ".well-known" / "skills" / "index.json"
    if not index_path.exists():
        return [_issue("warning", "missing-index", ".well-known/skills/index.json not found", index_path)]
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [_issue("error", "bad-index-json", f"invalid index JSON: {exc}", index_path)]
    rows = index.get("skills")
    if not isinstance(rows, list):
        return [_issue("error", "bad-index-shape", "index.skills must be a list", index_path)]

    actual = {p.name: p for p in skill_dirs}
    indexed: dict[str, dict[str, Any]] = {}
    for row_no, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            issues.append(_issue("error", "bad-index-row", "index skill row must be an object", f"{index_path}:{row_no}"))
            continue
        name = str(row.get("name", "")).strip()
        if not name:
            issues.append(_issue("error", "missing-index-name", "index skill row missing name", f"{index_path}:{row_no}"))
            continue
        if name in indexed:
            issues.append(_issue("error", "duplicate-index-name", f"duplicate index skill {name}", f"{index_path}:{row_no}", name))
        indexed[name] = row
        if name not in actual:
            issues.append(_issue("warning", "index-extra-skill", f"index references missing skill directory {name}", f"{index_path}:{row_no}", name))
            continue
        files = row.get("files", [])
        if not isinstance(files, list):
            issues.append(_issue("error", "bad-index-files", "index files must be a list", f"{index_path}:{row_no}", name))
            continue
        for file_name in files:
            file_path = actual[name] / str(file_name)
            if not file_path.exists():
                issues.append(_issue("error", "index-file-missing", f"index file does not exist: {file_name}", file_path, name))

        skill, load_issue = load_skill(actual[name])
        if load_issue:
            issues.append(load_issue)
            continue
        assert skill is not None
        index_desc = normalize_description(row.get("description"))
        skill_desc = normalize_description(skill.frontmatter.get("description"))
        if index_desc and skill_desc and index_desc != skill_desc:
            issues.append(
                _issue(
                    "warning",
                    "index-description-mismatch",
                    "index description differs from SKILL.md frontmatter description",
                    f"{index_path}:{row_no}",
                    name,
                )
            )

    for skill_name in sorted(set(actual) - set(indexed)):
        issues.append(_issue("warning", "index-missing-skill", f"skill {skill_name} is missing from index", index_path, skill_name))
    return issues


def validate_repo(root: Path) -> list[ValidationIssue]:
    skill_dirs = iter_skill_dirs(root)
    issues: list[ValidationIssue] = []
    if not skill_dirs:
        issues.append(_issue("error", "no-skills", "no clickzetta-* skill directories found", root))
        return issues
    for skill_dir in skill_dirs:
        issues.extend(_validate_skill_metadata(skill_dir))
        _, eval_issues = load_eval_cases(skill_dir)
        issues.extend(eval_issues)
    issues.extend(_validate_index(root, skill_dirs))
    return issues


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate ClickZetta skill repository structure.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--strict-warnings", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args(argv)

    issues = validate_repo(Path(args.root).resolve())
    if args.json:
        print(json.dumps([issue.__dict__ for issue in issues], ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            print(f"[{issue.severity.upper()}] {issue.code}: {issue.path}: {issue.message}")
        errors = sum(1 for issue in issues if issue.severity == "error")
        warnings = sum(1 for issue in issues if issue.severity == "warning")
        print(f"Static validation completed: {errors} error(s), {warnings} warning(s)")

    has_error = any(issue.severity == "error" for issue in issues)
    has_warning = any(issue.severity == "warning" for issue in issues)
    return 1 if has_error or (args.strict_warnings and has_warning) else 0


if __name__ == "__main__":
    raise SystemExit(main())

