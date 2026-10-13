"""Default and Jev-backed fallback scorers for uncertain candidates."""

from __future__ import annotations

from reflex_search.scorers import JevScorer


class JevFallback:
    """Jev-backed fallback scorer for uncertain candidates.

    Conforms to the fallback callable signature ``(path, query, content) → float``
    so it can be passed directly as the *fallback* argument to
    :class:`~reflex_search.searcher.ReflexCodeSearcher`.

    Internally creates a :class:`JevScorer` and delegates scoring to it.
    Telemetry from the most recent call is available on the instance.
    """

    provider = "jev-fallback"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._scorer = JevScorer(api_key=api_key, model=model, timeout=timeout)
        self.last_latency_ms: float = 0.0
        self.last_cost: float = 0.0
        self.last_input_tokens: int = 0

    def __call__(self, path: str, query: str, content: str) -> float:
        score = self._scorer.score(path, query, content)
        self.last_latency_ms = self._scorer.last_latency_ms
        self.last_cost = self._scorer.last_cost
        self.last_input_tokens = self._scorer.last_input_tokens
        return score


def default_fallback_scorer(path: str, query: str, content: str) -> float:
    """Simple term-overlap fallback scorer for uncertain candidates."""
    query_terms = [part.lower() for part in query.replace("-", " ").split() if part]
    if not query_terms:
        return 0.0
    text = f"{path} {content}".lower()
    matches = sum(1 for term in query_terms if term in text)
    return min(matches / len(query_terms), 0.9)
