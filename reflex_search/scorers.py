"""Relevance scorers for reflex-code-search."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Callable

import httpx

logger = logging.getLogger(__name__)

_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
_DEFAULT_JEV_MODEL = "typesafe/jev-1.13"

# Stopwords that dilute term-overlap scoring
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "about", "up", "down", "it", "its", "this", "that", "these", "those",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
    "she", "her", "they", "them", "their", "what", "which", "who", "whom",
    "how", "where", "when", "why", "if", "or", "and", "but", "not", "no",
    "so", "than", "too", "very", "just", "also",
})

# Regex for extracting Python/JS/Go/Rust definitions from source
_DEFINITION_RE = re.compile(
    r"(?:^|\n)\s*(?:def|class|function|func|fn|const|let|var|type|interface|struct|enum)\s+(\w+)",
)


class LocalScorer:
    """Fast local scorer with bigram matching, definition boosting, and stopword filtering.

    Implements the ``Scorer`` protocol from ``reflex_search.models``.
    """

    provider = "local"

    def score(self, file_path: str, query: str, content: str) -> float:
        query_terms = self._tokenize(query)
        if not query_terms:
            return 0.0

        path_text = file_path.lower()
        content_preview = content[:4000].lower()
        n = len(query_terms)

        # --- Unigram matching (same as before but with stopwords removed) ---
        path_hits = sum(1 for t in query_terms if t in path_text)
        content_hits = sum(1 for t in query_terms if t in content_preview)

        path_score = 0.25 * (path_hits / n)
        content_score = 0.45 * (content_hits / n)

        # --- Bigram matching (phrase sensitivity) ---
        bigram_score = 0.0
        if n >= 2:
            bigrams = [f"{query_terms[i]} {query_terms[i+1]}" for i in range(n - 1)]
            path_bigram_hits = sum(1 for bg in bigrams if bg in path_text)
            content_bigram_hits = sum(1 for bg in bigrams if bg in content_preview)
            nb = len(bigrams)
            bigram_score = 0.15 * ((path_bigram_hits + content_bigram_hits) / nb)

        # --- Definition-aware boosting ---
        def_score = 0.0
        definitions = _DEFINITION_RE.findall(content_preview)
        if definitions:
            def_names = {d.lower() for d in definitions}
            def_hits = sum(1 for t in query_terms if any(t in dn for dn in def_names))
            def_score = 0.15 * (def_hits / n)

        total = path_score + content_score + bigram_score + def_score
        return round(min(total, 1.0), 4)

    @staticmethod
    def _tokenize(value: str) -> list[str]:
        parts = value.lower().replace("-", " ").replace("_", " ").split()
        return [p for p in parts if p and p not in _STOPWORDS]


class JevScorer:
    """Relevance scorer backed by the Jev Decisions API via OpenRouter.

    Uses the Jev **noul** primitive (calibrated yes/no probability) to judge
    whether a file contains the implementation that answers a query.
    Falls back to ``LocalScorer`` on API errors.

    Implements the ``Scorer`` protocol from ``reflex_search.models``.
    """

    provider = "jev"

    _NOUL_INSTRUCTION = (
        "Does this file contain the implementation or definition "
        "that directly answers the question?  "
        "Documentation or changelogs that merely mention the topic do not count."
    )

    _SECRET_PATTERNS = (
        "api_key", "api-key", "apikey",
        "secret", "password", "passwd",
        "token", "credential", "private_key",
        "private-key", "aws_access", "aws_secret",
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
        state_redactor: Callable[[str], str] | None = None,
    ) -> None:
        self._api_key_override = api_key
        self.model = model or os.environ.get("JEV_MODEL", _DEFAULT_JEV_MODEL)
        self._timeout = timeout
        self._state_redactor = state_redactor or self._default_redactor
        self._fallback = LocalScorer()
        self.last_latency_ms: float = 0.0
        self.last_cost: float = 0.0
        self.last_input_tokens: int = 0

    @classmethod
    def _default_redactor(cls, state: str) -> str:
        """Redact lines that look like they contain secrets."""
        lines = state.splitlines()
        redacted: list[str] = []
        for line in lines:
            lowered = line.lower()
            if any(pat in lowered for pat in cls._SECRET_PATTERNS):
                redacted.append("[REDACTED]")
            else:
                redacted.append(line)
        return "\n".join(redacted)

    def _get_api_key(self) -> str:
        if self._api_key_override is not None:
            return self._api_key_override
        return os.environ.get("OPENROUTER_API_KEY", "")

    def score(self, file_path: str, query: str, content: str) -> float:
        self.last_latency_ms = 0.0
        self.last_cost = 0.0
        self.last_input_tokens = 0

        api_key = self._get_api_key()
        if not api_key:
            logger.debug("No API key, falling back to local scorer")
            return self._fallback.score(file_path, query, content)

        state = self._state_redactor(f"File: {file_path}\n\n{content[:2000]}")
        payload = {
            "model": self.model,
            "state": state,
            "questions": {
                "relevance": {
                    "type": "noul",
                    "instructions": f"{self._NOUL_INSTRUCTION} Question: {query}",
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            t0 = time.perf_counter()
            resp = httpx.post(
                _DECISIONS_URL,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            self.last_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            if resp.status_code == 401:
                logger.warning("Jev API returned 401 — check OPENROUTER_API_KEY")
                return self._fallback.score(file_path, query, content)
            if resp.status_code == 429:
                logger.warning("Jev API rate limited (429), falling back to local")
                return self._fallback.score(file_path, query, content)

            resp.raise_for_status()
            body = resp.json()

            usage = body.get("usage", {})
            self.last_cost = usage.get("cost", 0.0)
            self.last_input_tokens = usage.get("input_tokens", 0)

            answer = body.get("answers", {}).get("relevance", {})
            raw_noul = answer.get("noul")
            if raw_noul is not None and isinstance(raw_noul, (int, float)):
                return round(min(max(float(raw_noul), 0.0), 1.0), 4)

            logger.warning("Jev returned no noul value, falling back to local")
            return self._fallback.score(file_path, query, content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Jev API error (%s), falling back to local", type(exc).__name__)
            return self._fallback.score(file_path, query, content)
