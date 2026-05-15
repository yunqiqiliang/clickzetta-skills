import re


def compute_context_transfer_score(
    output: str, patterns: list[dict]
) -> tuple[float, list[str], int]:
    """
    Returns (score 0.0-1.0, list of matched descriptions, total expected count).
    score = matched / total. Returns 1.0 if patterns is empty.
    """
    if not patterns:
        return 1.0, [], 0

    found = []
    for p in patterns:
        if re.search(p["pattern"], output, re.IGNORECASE):
            found.append(p["description"])

    score = len(found) / len(patterns)
    return score, found, len(patterns)
