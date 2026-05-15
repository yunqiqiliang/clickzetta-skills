import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import json
from parser import parse_stream_json

SAMPLE_STREAM = [
    {"type": "system", "subtype": "init", "session_id": "s1"},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Bash",
         "input": {"command": "cz-cli sql \"SELECT 1\"", "description": "run sql"}}
    ], "usage": {"input_tokens": 100, "output_tokens": 20,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
    {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "查询完成"}
    ], "usage": {"input_tokens": 10, "output_tokens": 5,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
    {"type": "result", "subtype": "success", "duration_ms": 5000,
     "result": "查询完成", "usage": {
         "input_tokens": 110, "output_tokens": 25,
         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}},
]

def make_jsonl(events):
    return "\n".join(json.dumps(e) for e in events)

def test_parse_duration():
    result = parse_stream_json(make_jsonl(SAMPLE_STREAM))
    assert result["total_time_ms"] == 5000

def test_parse_tool_calls():
    result = parse_stream_json(make_jsonl(SAMPLE_STREAM))
    assert result["tool_call_count"] == 1
    assert result["tool_sequence"] == ["Bash"]

def test_parse_tool_input_summary():
    result = parse_stream_json(make_jsonl(SAMPLE_STREAM))
    assert "cz-cli sql" in result["tool_calls"][0]["input_summary"]

def test_parse_final_output():
    result = parse_stream_json(make_jsonl(SAMPLE_STREAM))
    assert result["final_output"] == "查询完成"

def test_parse_agent_run_count_zero():
    result = parse_stream_json(make_jsonl(SAMPLE_STREAM))
    assert result["agent_run_count"] == 0

def test_parse_agent_run_count_nonzero():
    stream = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash",
             "input": {"command": "cz-cli agent run \"show tables\" --format a2a", "description": "delegate"}}
        ], "usage": {"input_tokens": 50, "output_tokens": 10,
                     "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}},
        {"type": "result", "subtype": "success", "duration_ms": 8000,
         "result": "done", "usage": {"input_tokens": 50, "output_tokens": 10,
                                      "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}},
    ]
    result = parse_stream_json(make_jsonl(stream))
    assert result["agent_run_count"] == 1
