"""Configurable agent command runner used by trigger and A/B evals."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AgentRun:
    status: str
    prompt: str
    output: str = ""
    error: str = ""
    returncode: int | None = None
    triggered_skills: list[str] = field(default_factory=list)


def _recursive_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _recursive_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _recursive_strings(item)


def detect_triggered_skills(output: str, known_skills: list[str]) -> list[str]:
    """Best-effort detection for streamed JSON or text traces.

    Agent CLIs differ in how they expose tool traces. This parser accepts JSONL
    event streams, plain JSON blobs, and plain text. It looks for known skill
    names in tool/read events first, then falls back to exact name mentions.
    """
    hits: set[str] = set()
    interesting_text: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            interesting_text.append(stripped)
            continue
        text = " ".join(_recursive_strings(obj))
        lowered = text.lower()
        if "skill" in lowered or "read" in lowered or "available_skills" in lowered:
            interesting_text.append(text)
    if not interesting_text:
        interesting_text = [output]
    joined = "\n".join(interesting_text)
    for skill in known_skills:
        if re.search(rf"(?<![a-z0-9-]){re.escape(skill)}(?![a-z0-9-])", joined):
            hits.add(skill)
    return sorted(hits)


def run_agent_command(
    prompt: str,
    known_skills: list[str],
    command_template: str | None = None,
    *,
    timeout: int = 180,
    cwd: Path | None = None,
    extra_placeholders: dict[str, str] | None = None,
) -> AgentRun:
    command_template = command_template or os.environ.get("SKILL_EVAL_AGENT_COMMAND")
    if not command_template:
        return AgentRun(
            status="skipped",
            prompt=prompt,
            error="No agent command configured. Set SKILL_EVAL_AGENT_COMMAND or pass --agent-command.",
        )

    placeholders = dict(extra_placeholders or {})
    prompt_from_template = "{prompt}" in command_template or "{prompt_file}" in command_template
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".prompt.txt", delete=False) as f:
        f.write(prompt)
        prompt_file = f.name
    placeholders.setdefault("prompt_file", prompt_file)
    placeholders.setdefault("prompt", prompt)

    try:
        command = command_template.format(**placeholders)
        argv = shlex.split(command)
        if not prompt_from_template:
            argv.append(prompt)
        completed = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
        return AgentRun(
            status="completed" if completed.returncode == 0 else "failed",
            prompt=prompt,
            output=output,
            error="" if completed.returncode == 0 else completed.stderr,
            returncode=completed.returncode,
            triggered_skills=detect_triggered_skills(output, known_skills),
        )
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") if isinstance(exc.stdout, str) else "") + (
            ("\n" + exc.stderr) if isinstance(exc.stderr, str) and exc.stderr else ""
        )
        return AgentRun(status="timeout", prompt=prompt, output=output, error=str(exc), triggered_skills=[])
    finally:
        try:
            Path(prompt_file).unlink()
        except OSError:
            pass
