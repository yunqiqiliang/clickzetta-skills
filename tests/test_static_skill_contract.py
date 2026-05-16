"""Static contract checks for the ClickZetta skill repository."""

from pathlib import Path

from skill_eval.static_validation import validate_repo


ROOT = Path(__file__).resolve().parents[1]


def test_skill_static_contract_has_no_errors():
    issues = validate_repo(ROOT)
    errors = [issue for issue in issues if issue.severity == "error"]
    assert not errors, "\n".join(
        f"{issue.code}: {issue.path}: {issue.message}" for issue in errors
    )

