"""REFLEX-style search loop orchestrator."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from reflex_search.fallback import JevFallback
from reflex_search.file_collector import collect_files, read_file
from reflex_search.gate import ConfidenceGate
from reflex_search.models import (
    GateDecision,
    Scorer,
    SearchResult,
    SearchSession,
    SessionTelemetry,
)
from reflex_search.scorers import JevScorer, LocalScorer


class ReflexCodeSearcher:
    """Minimal semantic code search using a REFLEX-style loop."""

    def __init__(
        self,
        repo_root: str | None = None,
        scorer: Scorer | None = None,
        fallback: Callable[[str, str, str], float] | None = None,
        accept_threshold: float = 0.65,
        uncertain_threshold: float = 0.40,
        min_margin: float = 0.0,
        top_k: int = 5,
    ) -> None:
        self.repo_root = repo_root or os.getcwd()
        self.scorer = scorer or LocalScorer()
        self.fallback = fallback
        if top_k < 0:
            raise ValueError("top_k must be non-negative")
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
        requested_top_k = self.top_k if top_k is None else top_k
        if requested_top_k < 0:
            raise ValueError("top_k must be non-negative")
        active_root = repo_root or self.repo_root
        candidates = collect_files(active_root)
        results: list[SearchResult] = []
        audit: list[dict[str, Any]] = []
        provider_name = getattr(self.scorer, "provider", "local")

        # Score every readable candidate first so the margin check can compare
        # the highest score with the actual runner-up.
        scored: list[tuple[str, str, float, dict[str, Any]]] = []
        for candidate in candidates:
            try:
                content = read_file(candidate, active_root)
            except OSError:
                continue
            score = self.scorer.score(candidate, query, content)
            call_telemetry: dict[str, Any] = {}
            if isinstance(self.scorer, JevScorer):
                call_telemetry = {
                    "latency_ms": self.scorer.last_latency_ms,
                    "cost": self.scorer.last_cost,
                    "input_tokens": self.scorer.last_input_tokens,
                }
            scored.append((candidate, content, score, call_telemetry))

        ranked = sorted(scored, key=lambda item: item[2], reverse=True)
        top_runner_up = ranked[1][2] if len(ranked) > 1 else 0.0

        for candidate, content, score, telemetry in scored:
            decision = self.gate.decide(
                score,
                runner_up=top_runner_up if ranked and ranked[0][0] == candidate else 0.0,
            )

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
                    "step": len(audit) + 1,
                    "provider": provider_name,
                    "score": score,
                    "decision": decision.value,
                    "path": candidate,
                    **telemetry,
                })
                continue

            if decision is GateDecision.UNCERTAIN and self.fallback is not None:
                audit.append({
                    "step": len(audit) + 1,
                    "provider": provider_name,
                    "score": score,
                    "decision": decision.value,
                    "path": candidate,
                    **telemetry,
                })
                fb_score = self.fallback(candidate, query, content)
                fb_decision = self.gate.decide(fb_score)

                fb_provider = getattr(self.fallback, "provider", "fallback")
                fb_telemetry: dict[str, Any] = {}
                if isinstance(self.fallback, JevFallback):
                    fb_telemetry = {
                        "latency_ms": self.fallback.last_latency_ms,
                        "cost": self.fallback.last_cost,
                        "input_tokens": self.fallback.last_input_tokens,
                    }

                if fb_decision is GateDecision.ACCEPT:
                    results.append(
                        SearchResult(
                            path=candidate,
                            score=fb_score,
                            provider=fb_provider,
                            reason="Escalated from uncertain; accepted by fallback",
                            excerpt=self._excerpt(content, query),
                        )
                    )
                    audit.append({
                        "step": len(audit) + 1,
                        "provider": fb_provider,
                        "score": fb_score,
                        "decision": "accept",
                        "path": candidate,
                        **fb_telemetry,
                    })
                    continue

                audit.append({
                    "step": len(audit) + 1,
                    "provider": fb_provider,
                    "score": fb_score,
                    "decision": "reject",
                    "path": candidate,
                    **fb_telemetry,
                })
                continue

            audit.append({
                "step": len(audit) + 1,
                "provider": provider_name,
                "score": score,
                "decision": decision.value,
                "path": candidate,
                **telemetry,
            })

        results.sort(key=lambda r: r.score, reverse=True)
        limit = min(requested_top_k, len(results))

        telemetry_summary = self._compute_telemetry(audit)

        return SearchSession(
            query=query,
            repo_root=active_root,
            results=results[:limit],
            audit_trail=audit,
            telemetry=telemetry_summary,
        )

    def search_two_pass(
        self,
        query: str,
        jev_scorer: JevScorer | None = None,
        repo_root: str | None = None,
        top_k: int | None = None,
        shortlist_size: int = 20,
    ) -> SearchSession:
        """Two-pass search: LocalScorer narrows, JevScorer re-scores the shortlist."""
        requested_top_k = self.top_k if top_k is None else top_k
        if requested_top_k < 0:
            raise ValueError("top_k must be non-negative")
        if shortlist_size < 0:
            raise ValueError("shortlist_size must be non-negative")
        active_root = repo_root or self.repo_root
        candidates = collect_files(active_root)
        audit: list[dict[str, Any]] = []

        # --- Pass 1: LocalScorer scores all files, keep top N ---
        local = LocalScorer()
        scored: list[tuple[str, float, str]] = []  # (path, score, content)

        for index, candidate in enumerate(candidates, start=1):
            try:
                content = read_file(candidate, active_root)
            except OSError:
                continue

            score = local.score(candidate, query, content)
            scored.append((candidate, score, content))

            audit.append({
                "step": len(audit) + 1,
                "provider": "local",
                "score": score,
                "decision": "prefilter",
                "path": candidate,
            })

        scored.sort(key=lambda t: t[1], reverse=True)
        shortlist = scored[:shortlist_size]

        # --- Pass 2: JevScorer re-scores the shortlist ---
        jev = jev_scorer or JevScorer()
        results: list[SearchResult] = []
        pass2_start = len(audit)

        jev_scored: list[tuple[str, str, float, dict[str, Any]]] = []

        for i, (candidate, _local_score, content) in enumerate(shortlist, start=1):
            score = jev.score(candidate, query, content)
            telemetry: dict[str, Any] = {
                "latency_ms": jev.last_latency_ms,
                "cost": jev.last_cost,
                "input_tokens": jev.last_input_tokens,
            }
            jev_scored.append((candidate, content, score, telemetry))

        jev_ranked = sorted(jev_scored, key=lambda item: item[2], reverse=True)
        top_runner_up = jev_ranked[1][2] if len(jev_ranked) > 1 else 0.0

        for i, (candidate, content, score, telemetry) in enumerate(jev_scored, start=1):
            decision = self.gate.decide(
                score,
                runner_up=top_runner_up if jev_ranked and jev_ranked[0][0] == candidate else 0.0,
            )

            if decision is GateDecision.ACCEPT:
                results.append(
                    SearchResult(
                        path=candidate,
                        score=score,
                        provider="jev",
                        reason="Accepted by Jev (two-pass)",
                        excerpt=self._excerpt(content, query),
                    )
                )

            audit.append({
                "step": pass2_start + i,
                "provider": "jev",
                "score": score,
                "decision": decision.value,
                "path": candidate,
                **telemetry,
            })

        results.sort(key=lambda r: r.score, reverse=True)
        limit = min(requested_top_k, len(results))

        telemetry_summary = self._compute_telemetry(audit)

        return SearchSession(
            query=query,
            repo_root=active_root,
            results=results[:limit],
            audit_trail=audit,
            telemetry=telemetry_summary,
        )

    @staticmethod
    def _compute_telemetry(audit: list[dict[str, Any]]) -> SessionTelemetry:
        accepted = 0
        uncertain = 0
        rejected = 0
        fallback_calls = 0
        total_latency = 0.0
        total_cost = 0.0
        total_tokens = 0

        for step in audit:
            decision = step.get("decision", "")
            provider = step.get("provider", "")

            if decision == "accept":
                accepted += 1
            elif decision == "uncertain":
                uncertain += 1
            elif decision == "reject":
                rejected += 1

            if provider in ("fallback", "jev-fallback"):
                fallback_calls += 1

            total_latency += step.get("latency_ms", 0.0)
            total_cost += step.get("cost", 0.0)
            total_tokens += step.get("input_tokens", 0)

        return SessionTelemetry(
            files_scanned=len({step.get("path") for step in audit if step.get("path")}),
            accepted=accepted,
            uncertain=uncertain,
            rejected=rejected,
            fallback_calls=fallback_calls,
            total_latency_ms=round(total_latency, 2),
            total_cost=round(total_cost, 6),
            total_tokens=total_tokens,
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
