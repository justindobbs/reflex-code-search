"""REFLEX-style search loop orchestrator."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from reflex_search.file_collector import collect_files, read_file
from reflex_search.gate import ConfidenceGate
from reflex_search.models import GateDecision, SearchResult, SearchSession
from reflex_search.scorers import JevScorer, LocalScorer


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
        candidates = collect_files(active_root)
        results: list[SearchResult] = []
        audit: list[dict[str, Any]] = []
        provider_name = getattr(self.scorer, "provider", "local")

        for index, candidate in enumerate(candidates, start=1):
            try:
                content = read_file(candidate, active_root)
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
