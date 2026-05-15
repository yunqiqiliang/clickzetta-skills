import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scorer import compute_context_transfer_score

PATTERNS = [
    {"pattern": r"\b(user_id|tenant_id)\b", "description": "字段名"},
    {"pattern": r"\d[\d,]+ (行|rows)", "description": "行数"},
]

def test_full_match():
    output = "表有字段 user_id, tenant_id，共 1,234,567 行"
    score, found, expected = compute_context_transfer_score(output, PATTERNS)
    assert score == 1.0
    assert len(found) == 2
    assert expected == 2

def test_partial_match():
    output = "表有字段 user_id，但没有行数信息"
    score, found, expected = compute_context_transfer_score(output, PATTERNS)
    assert score == 0.5
    assert len(found) == 1

def test_no_match():
    output = "根据表结构，建议创建同步任务"
    score, found, expected = compute_context_transfer_score(output, PATTERNS)
    assert score == 0.0
    assert len(found) == 0

def test_empty_patterns():
    score, found, expected = compute_context_transfer_score("any output", [])
    assert score == 1.0
    assert expected == 0
