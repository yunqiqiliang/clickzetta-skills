import json


def parse_stream_json(jsonl_text: str) -> dict:
    """Parse claude --output-format stream-json output into a structured RunResult."""
    tool_calls = []
    final_output = ""
    total_time_ms = 0
    input_tokens = 0
    output_tokens = 0
    cache_read_tokens = 0

    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = event.get("type", "")

        if etype == "assistant":
            msg = event.get("message", {})
            usage = msg.get("usage", {})
            input_tokens += usage.get("input_tokens", 0)
            output_tokens += usage.get("output_tokens", 0)
            cache_read_tokens += usage.get("cache_read_input_tokens", 0)

            for block in msg.get("content", []):
                if block.get("type") == "tool_use":
                    inp = block.get("input", {})
                    cmd = inp.get("command", inp.get("prompt", str(inp)))
                    tool_calls.append({
                        "name": block.get("name", ""),
                        "input_summary": cmd[:200],
                    })

        elif etype == "result":
            total_time_ms = event.get("duration_ms", 0)
            final_output = event.get("result", "")
            usage = event.get("usage", {})
            if usage.get("input_tokens"):
                input_tokens = usage["input_tokens"]
            if usage.get("output_tokens"):
                output_tokens = usage["output_tokens"]
            if usage.get("cache_read_input_tokens"):
                cache_read_tokens = usage["cache_read_input_tokens"]

    agent_run_count = sum(
        1 for tc in tool_calls
        if "cz-cli agent run" in tc["input_summary"]
    )

    return {
        "total_time_ms": total_time_ms,
        "tool_call_count": len(tool_calls),
        "tool_sequence": [tc["name"] for tc in tool_calls],
        "tool_calls": tool_calls,
        "agent_run_count": agent_run_count,
        "final_output": final_output,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
    }
