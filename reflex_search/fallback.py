"""Default fallback scorer for uncertain candidates."""

from __future__ import annotations


def default_fallback_scorer(path: str, query: str, content: str) -> float:
    """Simple term-overlap fallback scorer for uncertain candidates."""
    query_terms = [part.lower() for part in query.replace("-", " ").split() if part]
    if not query_terms:
        return 0.0
    text = f"{path} {content}".lower()
    matches = sum(1 for term in query_terms if term in text)
    return min(matches / len(query_terms), 0.9)
