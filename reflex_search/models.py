"""Data models, protocols, and configuration for reflex-code-search."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class GateDecision(Enum):
    """Three-way gate outcome for the REFLEX control loop."""

    ACCEPT = "accept"
    UNCERTAIN = "uncertain"
    REJECT = "reject"


@dataclass
class SearchResult:
    path: str
    score: float
    provider: str
    reason: str
    excerpt: str = ""


@dataclass
class SearchCandidate:
    """Ranked lead that did not pass the accept threshold."""

    path: str
    score: float
    provider: str
    decision: str
    reason: str
    excerpt: str = ""


@dataclass
class SessionTelemetry:
    """Aggregate telemetry for a search session."""

    files_scanned: int = 0
    accepted: int = 0
    uncertain: int = 0
    rejected: int = 0
    fallback_calls: int = 0
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    total_tokens: int = 0


@dataclass
class SearchSession:
    """Accepted results, lower-confidence candidates, and search audit data."""

    query: str
    repo_root: str
    results: list[SearchResult] = field(default_factory=list)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)
    telemetry: SessionTelemetry | None = None
    candidates: list[SearchCandidate] = field(default_factory=list)


@runtime_checkable
class Scorer(Protocol):
    """Interface for pluggable relevance scorers."""

    def score(self, file_path: str, query: str, content: str) -> float: ...


__all__ = [
    "GateDecision",
    "Scorer",
    "SearchCandidate",
    "SearchResult",
    "SearchSession",
    "SessionTelemetry",
]
