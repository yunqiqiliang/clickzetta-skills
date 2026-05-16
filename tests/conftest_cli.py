"""
Shared fixtures for cz-cli skill validation tests.

Usage:
    python -m pytest tests/test_cli_*.py -v

Requires the 'skill_test' profile in ~/.clickzetta/profiles.toml.
The profile is auto-configured from .env by running:
    cz-cli profile create skill_test ...
"""
import json
import subprocess
import pytest


CLI_PROFILE = "skill_test"


def cz(args: list[str], check_error: bool = True) -> dict:
    """Run a cz-cli command with the skill_test profile and return parsed JSON output."""
    cmd = ["cz-cli", "--profile", CLI_PROFILE] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    raw = result.stdout.strip() or result.stderr.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"_raw": raw, "_returncode": result.returncode}
    if check_error and result.returncode != 0 and "error" in data:
        pytest.fail(f"cz-cli command failed: {cmd}\n{raw}")
    return data


def cz_ok(args: list[str]) -> dict:
    """Run a cz-cli command and assert it succeeds (no error key)."""
    data = cz(args, check_error=False)
    assert "error" not in data, f"Expected success but got error:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
    return data


def cz_expect_error(args: list[str]) -> dict:
    """Run a cz-cli command and assert it returns an error."""
    data = cz(args, check_error=False)
    assert "error" in data or data.get("_returncode", 0) != 0, \
        f"Expected error but command succeeded:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
    return data


@pytest.fixture(scope="session")
def cli():
    """Session-scoped fixture providing the cz() helper."""
    return cz
