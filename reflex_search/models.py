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
class SearchSession:
    query: str
    repo_root: str
    results: list[SearchResult] = field(default_factory=list)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)


@runtime_checkable
class Scorer(Protocol):
    """Interface for pluggable relevance scorers."""

    def score(self, file_path: str, query: str, content: str) -> float: ...


__all__ = [
    "GateDecision",
    "Scorer",
    "SearchResult",
    "SearchSession",
]
