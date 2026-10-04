"""Core REFLEX-style search logic."""

from __future__ import annotations

import logging
import math
import os
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from reflex_search.models import GateDecision, SearchResult, SearchSession

logger = logging.getLogger(__name__)

_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
_DEFAULT_JEV_MODEL = "typesafe/jev-1.13"

DEFAULT_TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
}

DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".idea",
    ".vscode",
    ".DS_Store",
    ".env",
}

_EXCLUDE_SUFFIXES = {".egg-info"}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class LocalScorer:
    """Fast local term-overlap scorer (no API calls).

    Implements the ``Scorer`` protocol from ``reflex_search.models``.
    """

    provider = "local"

    def score(self, file_path: str, query: str, content: str) -> float:
        query_terms = self._tokenize(query)
        if not query_terms:
            return 0.0

        path_text = file_path.lower()
        content_preview = content[:2000].lower()
        n = len(query_terms)

        path_hits = sum(1 for t in query_terms if t in path_text)
        content_hits = sum(1 for t in query_terms if t in content_preview)

        path_score = 0.30 * (path_hits / n)
        content_score = 0.70 * (content_hits / n)

        return round(min(path_score + content_score, 1.0), 4)

    @staticmethod
    def _tokenize(value: str) -> list[str]:
        return [part for part in value.lower().replace("-", " ").split() if part]


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
        except Exception as exc:
            logger.warning("Jev API error (%s), falling back to local", type(exc).__name__)
            return self._fallback.score(file_path, query, content)


def default_fallback_scorer(path: str, query: str, content: str) -> float:
    """Simple term-overlap fallback scorer for uncertain candidates."""
    query_terms = [part.lower() for part in query.replace("-", " ").split() if part]
    if not query_terms:
        return 0.0
    text = f"{path} {content}".lower()
    matches = sum(1 for term in query_terms if term in text)
    return min(matches / len(query_terms), 0.9)


# ---------------------------------------------------------------------------
# Confidence gate
# ---------------------------------------------------------------------------

class ConfidenceGate:
    """Three-way gate for the REFLEX search loop.

    - **accept**: score >= *accept_threshold*
    - **uncertain**: score >= *uncertain_threshold* but below accept
    - **reject**: score < *uncertain_threshold*

    The optional *min_margin* parameter (ported from tracecore-reflex)
    requires the top candidate to lead the runner-up by at least this
    margin before being accepted.  When the margin check fails, the
    decision is downgraded to **uncertain**.
    """

    def __init__(
        self,
        accept_threshold: float = 0.65,
        uncertain_threshold: float = 0.40,
        min_margin: float = 0.0,
    ) -> None:
        self.accept_threshold = accept_threshold
        self.uncertain_threshold = uncertain_threshold
        self.min_margin = min_margin

    def decide(self, score: float, runner_up: float = 0.0) -> GateDecision:
        if not isinstance(score, (int, float)) or not math.isfinite(score):
            return GateDecision.REJECT
        score = min(max(float(score), 0.0), 1.0)

        if score < self.uncertain_threshold:
            return GateDecision.REJECT

        if score >= self.accept_threshold:
            if self.min_margin > 0.0 and (score - runner_up) < self.min_margin:
                return GateDecision.UNCERTAIN
            return GateDecision.ACCEPT

        return GateDecision.UNCERTAIN


# ---------------------------------------------------------------------------
# Search loop
# ---------------------------------------------------------------------------

class ReflexCodeSearcher:
    """Minimal semantic code search using a REFLEX-style loop."""

    def __init__(
        self,
        repo_root: str | None = None,
        scorer: LocalScorer | JevScorer | None = None,
        fallback: Callable[[str, str, str], float] | None = None,
        accept_threshold: float = 0.65,
        uncertain_threshold: float = 0.40,
        min_margin: float = 0.0,
        top_k: int = 5,
    ) -> None:
        self.repo_root = repo_root or os.getcwd()
        self.scorer = scorer or LocalScorer()
        self.fallback = fallback
        self.top_k = top_k
        self.gate = ConfidenceGate(
            accept_threshold=accept_threshold,
            uncertain_threshold=uncertain_threshold,
            min_margin=min_margin,
        )

    def search(
        self,
        query: str,
        repo_root: str | None = None,
        top_k: int | None = None,
    ) -> SearchSession:
        active_root = repo_root or self.repo_root
        candidates = self._collect_files(active_root)
        results: list[SearchResult] = []
        audit: list[dict[str, Any]] = []
        provider_name = getattr(self.scorer, "provider", "local")

        for index, candidate in enumerate(candidates, start=1):
            try:
                content = self._read_file(candidate, active_root)
            except OSError:
                continue

            score = self.scorer.score(candidate, query, content)
            decision = self.gate.decide(score)

            telemetry: dict[str, Any] = {}
            if isinstance(self.scorer, JevScorer):
                telemetry = {
                    "latency_ms": self.scorer.last_latency_ms,
                    "cost": self.scorer.last_cost,
                    "input_tokens": self.scorer.last_input_tokens,
                }

            if decision is GateDecision.ACCEPT:
                results.append(
                    SearchResult(
                        path=candidate,
                        score=score,
                        provider=provider_name,
                        reason="Accepted by confidence gate",
                        excerpt=self._excerpt(content, query),
                    )
                )
                audit.append({
                    "step": index,
                    "provider": provider_name,
                    "score": score,
                    "decision": decision.value,
                    "path": candidate,
                    **telemetry,
                })
                continue

            if decision is GateDecision.UNCERTAIN and self.fallback is not None:
                fb_score = self.fallback(candidate, query, content)
                fb_decision = self.gate.decide(fb_score)

                if fb_decision is GateDecision.ACCEPT:
                    results.append(
                        SearchResult(
                            path=candidate,
                            score=fb_score,
                            provider="fallback",
                            reason="Escalated from uncertain; accepted by fallback",
                            excerpt=self._excerpt(content, query),
                        )
                    )
                    audit.append({
                        "step": index,
                        "provider": "fallback",
                        "score": fb_score,
                        "decision": "accept",
                        "path": candidate,
                        **telemetry,
                    })
                    continue

                audit.append({
                    "step": index,
                    "provider": "fallback",
                    "score": fb_score,
                    "decision": "reject",
                    "path": candidate,
                    **telemetry,
                })
                continue

            audit.append({
                "step": index,
                "provider": provider_name,
                "score": score,
                "decision": decision.value,
                "path": candidate,
                **telemetry,
            })

        results.sort(key=lambda r: r.score, reverse=True)
        limit = min(top_k or self.top_k, len(results))

        return SearchSession(
            query=query,
            repo_root=active_root,
            results=results[:limit],
            audit_trail=audit,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _collect_files(self, repo_root: str) -> list[str]:
        root = Path(repo_root)
        files: list[str] = []

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in DEFAULT_EXCLUDES for part in path.parts):
                continue
            if any(part.endswith(sfx) for part in path.parts for sfx in _EXCLUDE_SUFFIXES):
                continue
            if path.suffix.lower() not in DEFAULT_TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 250_000:
                    continue
            except OSError:
                continue
            files.append(str(path.relative_to(root)))

        files.sort()
        return files

    @staticmethod
    def _read_file(relative_path: str, repo_root: str) -> str:
        root = Path(repo_root)
        return (root / relative_path).read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _excerpt(content: str, query: str) -> str:
        query_terms = [t.lower() for t in query.replace("-", " ").split() if t]
        lines = content.splitlines()
        matches: list[str] = []

        for line in lines:
            lowered = line.lower()
            if any(term in lowered for term in query_terms):
                matches.append(line.strip())
                if len(matches) >= 3:
                    break

        if not matches:
            excerpt = "\n".join(lines[:3])
        else:
            excerpt = "\n".join(matches)

        return excerpt[:400]
