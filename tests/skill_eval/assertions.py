"""Output assertions for skill A/B evals."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .core import EvalCase


@dataclass(frozen=True)
class AssertionResult:
    passed: bool
    failures: list[str] = field(default_factory=list)


def evaluate_output(output: str, case: EvalCase) -> AssertionResult:
    failures: list[str] = []
    for needle in case.expected_output_contains:
        if needle not in output:
            failures.append(f"missing expected text: {needle!r}")
    for needle in case.expected_output_not_contains:
        if needle in output:
            failures.append(f"found forbidden text: {needle!r}")

    for assertion in case.assertions:
        kind = assertion.get("type")
        value = str(assertion.get("value", ""))
        if kind == "contains" and value not in output:
            failures.append(f"missing assertion text: {value!r}")
        elif kind == "not_contains" and value in output:
            failures.append(f"found forbidden assertion text: {value!r}")
        elif kind == "regex" and not re.search(value, output, re.DOTALL):
            failures.append(f"regex did not match: {value!r}")
        elif kind in {"contains", "not_contains", "regex"}:
            continue
        else:
            failures.append(f"unsupported assertion type: {kind!r}")
    return AssertionResult(passed=not failures, failures=failures)


def result_to_dict(result: AssertionResult) -> dict[str, Any]:
    return {"passed": result.passed, "failures": result.failures}

