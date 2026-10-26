"""REFLEX-style search loop orchestrator."""

from __future__ import annotations

import ast
import asyncio
import math
import os
import re
from collections.abc import Callable
from typing import Any

from reflex_search.fallback import JevFallback
from reflex_search.file_collector import collect_files, read_file
from reflex_search.gate import ConfidenceGate
from reflex_search.models import (
    GateDecision,
    Scorer,
    SearchCandidate,
    SearchResult,
    SearchSession,
    SessionTelemetry,
)
from reflex_search.scorers import AsyncJevScorer, JevScorer, LocalScorer


class ReflexCodeSearcher:
    """Minimal semantic code search using a REFLEX-style loop."""

    _DEFINITION_LINE_RE = re.compile(
        r"^\s*(?:async\s+)?(?:def|class|function|func|fn|const|let|var|type|"
        r"interface|struct|enum)\s+[\w$]+"
    )
    _EXCERPT_GENERIC_TERMS = frozenset(
        {"implement", "define", "work", "method", "function", "class", "file", "code"}
    )

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
        suggestions: list[SearchCandidate] = []
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
                    "decision": fb_decision.value,
                    "path": candidate,
                    **fb_telemetry,
                })
                if self._has_candidate_score(fb_score):
                    suggestions.append(
                        SearchCandidate(
                            path=candidate,
                            score=fb_score,
                            provider=fb_provider,
                            decision=fb_decision.value,
                            reason="Fallback did not pass the accept gate",
                            excerpt=self._excerpt(content, query),
                        )
                    )
                continue

            audit.append({
                "step": len(audit) + 1,
                "provider": provider_name,
                "score": score,
                "decision": decision.value,
                "path": candidate,
                **telemetry,
            })
            if self._has_candidate_score(score):
                suggestions.append(
                    SearchCandidate(
                        path=candidate,
                        score=score,
                        provider=provider_name,
                        decision=decision.value,
                        reason=self._candidate_reason(decision),
                        excerpt=self._excerpt(content, query),
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        suggestions.sort(key=lambda r: r.score, reverse=True)
        limit = min(requested_top_k, len(results))
        candidate_limit = min(requested_top_k, len(suggestions))

        telemetry_summary = self._compute_telemetry(audit)

        return SearchSession(
            query=query,
            repo_root=active_root,
            results=results[:limit],
            audit_trail=audit,
            telemetry=telemetry_summary,
            candidates=suggestions[:candidate_limit],
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
        suggestions: list[SearchCandidate] = []
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
            elif self._has_candidate_score(score):
                suggestions.append(
                    SearchCandidate(
                        path=candidate,
                        score=score,
                        provider="jev",
                        decision=decision.value,
                        reason=self._candidate_reason(decision),
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
        suggestions.sort(key=lambda r: r.score, reverse=True)
        limit = min(requested_top_k, len(results))
        candidate_limit = min(requested_top_k, len(suggestions))

        telemetry_summary = self._compute_telemetry(audit)

        return SearchSession(
            query=query,
            repo_root=active_root,
            results=results[:limit],
            audit_trail=audit,
            telemetry=telemetry_summary,
            candidates=suggestions[:candidate_limit],
        )

    @staticmethod
    def _candidate_reason(decision: GateDecision) -> str:
        if decision is GateDecision.UNCERTAIN:
            return "Uncertain candidate; did not pass the accept gate"
        return "Low-confidence candidate; shown for manual inspection"

    @staticmethod
    def _has_candidate_score(score: Any) -> bool:
        return isinstance(score, (int, float)) and math.isfinite(score) and score > 0

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
        lines = content.splitlines()
        query_terms = set(LocalScorer._tokenize(query))
        query_terms.difference_update(ReflexCodeSearcher._EXCERPT_GENERIC_TERMS)
        best_index: int | None = None
        best_score = 0

        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith(("import ", "from ", "#", "//", "/*", "*", "<!--")):
                continue

            line_terms = set(LocalScorer._tokenize(line))
            overlap = len(query_terms & line_terms)
            if not overlap:
                continue

            # Prefer declaration lines when they contain query terms. Exact
            # token matching avoids treating e.g. "asyncio" as "async".
            score = overlap + int(bool(ReflexCodeSearcher._DEFINITION_LINE_RE.match(line)))
            if score > best_score:
                best_index = index
                best_score = score

        if best_index is None:
            # A query may describe behavior without using words present in the
            # source. In that case, show a declaration instead of imports.
            best_index = next(
                (
                    index
                    for index, line in enumerate(lines)
                    if ReflexCodeSearcher._DEFINITION_LINE_RE.match(line)
                ),
                next((index for index, line in enumerate(lines) if line.strip()), 0),
            )

        python_excerpt = ReflexCodeSearcher._python_definition_excerpt(content, lines, best_index)
        if python_excerpt is not None:
            return python_excerpt[:600]

        start = max(0, best_index - 1)
        end = min(len(lines), best_index + 8)
        excerpt_lines = [
            f"{index + 1}: {lines[index].rstrip()}"
            for index in range(start, end)
            if lines[index].strip()
        ]

        excerpt = "\n".join(excerpt_lines)
        return excerpt[:600]

    @staticmethod
    def _python_definition_excerpt(content: str, lines: list[str], line_index: int) -> str | None:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None

        definition = next(
            (
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef))
                and node.lineno == line_index + 1
            ),
            None,
        )
        if definition is None:
            return None

        body = definition.body
        first_body_line = body[0].lineno if body else None
        if (
            len(body) > 1
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body = body[1:]

        if not body:
            return None

        signature_end = (first_body_line or body[0].lineno) - 2
        selected_indices = [line_index]
        if signature_end > line_index:
            if signature_end - line_index <= 4:
                selected_indices.extend(range(line_index + 1, signature_end + 1))
            else:
                selected_indices.append(signature_end)

        body_start = body[0].lineno - 1
        body_end = min(definition.end_lineno or len(lines), body_start + 5)
        selected_indices.extend(range(body_start, body_end))

        return "\n".join(
            f"{index + 1}: {lines[index].rstrip()}"
            for index in selected_indices
            if 0 <= index < len(lines) and lines[index].strip()
        )

    # ------------------------------------------------------------------
    # Async variants — parallel Jev scoring via asyncio
    # ------------------------------------------------------------------

    async def async_search(
        self,
        query: str,
        repo_root: str | None = None,
        top_k: int | None = None,
        async_scorer: AsyncJevScorer | None = None,
        concurrency: int = 10,
    ) -> SearchSession:
        """Local scoring + parallel async Jev fallback for uncertain candidates.

        Pass 1 scores every file with the instance's (typically local) scorer
        synchronously.  Uncertain candidates are then re-scored in parallel
        using *async_scorer* (defaults to a fresh ``AsyncJevScorer``).
        """
        requested_top_k = self.top_k if top_k is None else top_k
        if requested_top_k < 0:
            raise ValueError("top_k must be non-negative")
        active_root = repo_root or self.repo_root
        candidates = collect_files(active_root)
        results: list[SearchResult] = []
        suggestions: list[SearchCandidate] = []
        audit: list[dict[str, Any]] = []
        provider_name = getattr(self.scorer, "provider", "local")

        # --- Pass 1: score all files with the sync scorer ---
        scored: list[tuple[str, str, float]] = []
        for candidate in candidates:
            try:
                content = read_file(candidate, active_root)
            except OSError:
                continue
            score = self.scorer.score(candidate, query, content)
            scored.append((candidate, content, score))

        ranked = sorted(scored, key=lambda t: t[2], reverse=True)
        top_runner_up = ranked[1][2] if len(ranked) > 1 else 0.0

        accepted: list[tuple[str, str, float]] = []
        uncertain: list[tuple[str, str, float]] = []

        for candidate, content, score in scored:
            decision = self.gate.decide(
                score,
                runner_up=top_runner_up if ranked and ranked[0][0] == candidate else 0.0,
            )
            audit.append({
                "step": len(audit) + 1,
                "provider": provider_name,
                "score": score,
                "decision": decision.value,
                "path": candidate,
            })
            if decision is GateDecision.ACCEPT:
                accepted.append((candidate, content, score))
            elif decision is GateDecision.UNCERTAIN:
                uncertain.append((candidate, content, score))
            elif self._has_candidate_score(score):
                suggestions.append(
                    SearchCandidate(
                        path=candidate,
                        score=score,
                        provider=provider_name,
                        decision=decision.value,
                        reason=self._candidate_reason(decision),
                        excerpt=self._excerpt(content, query),
                    )
                )

        # Add accepted results immediately
        for candidate, content, score in accepted:
            results.append(
                SearchResult(
                    path=candidate,
                    score=score,
                    provider=provider_name,
                    reason="Accepted by confidence gate",
                    excerpt=self._excerpt(content, query),
                )
            )

        # --- Pass 2: parallel async Jev scoring for uncertain candidates ---
        if uncertain:
            jev = async_scorer or AsyncJevScorer()
            sem = asyncio.Semaphore(concurrency)

            async def _score_one(path: str, q: str, cont: str) -> tuple[str, str, float, dict[str, Any]]:
                async with sem:
                    s = await jev.score(path, q, cont)
                    telemetry: dict[str, Any] = {
                        "latency_ms": jev.last_latency_ms,
                        "cost": jev.last_cost,
                        "input_tokens": jev.last_input_tokens,
                    }
                    return path, cont, s, telemetry

            tasks = [_score_one(c, query, cont) for c, cont, _ in uncertain]
            fb_results = await asyncio.gather(*tasks)

            for candidate, content, fb_score, fb_telemetry in fb_results:
                fb_decision = self.gate.decide(fb_score)
                fb_provider = jev.provider
                if fb_decision is GateDecision.ACCEPT:
                    results.append(
                        SearchResult(
                            path=candidate,
                            score=fb_score,
                            provider=fb_provider,
                            reason="Escalated from uncertain; accepted by async fallback",
                            excerpt=self._excerpt(content, query),
                        )
                    )
                elif self._has_candidate_score(fb_score):
                    suggestions.append(
                        SearchCandidate(
                            path=candidate,
                            score=fb_score,
                            provider=fb_provider,
                            decision=fb_decision.value,
                            reason="Async fallback did not pass the accept gate",
                            excerpt=self._excerpt(content, query),
                        )
                    )
                audit.append({
                    "step": len(audit) + 1,
                    "provider": fb_provider,
                    "score": fb_score,
                    "decision": fb_decision.value,
                    "path": candidate,
                    **fb_telemetry,
                })

        results.sort(key=lambda r: r.score, reverse=True)
        suggestions.sort(key=lambda r: r.score, reverse=True)
        limit = min(requested_top_k, len(results))
        candidate_limit = min(requested_top_k, len(suggestions))
        telemetry_summary = self._compute_telemetry(audit)

        return SearchSession(
            query=query,
            repo_root=active_root,
            results=results[:limit],
            audit_trail=audit,
            telemetry=telemetry_summary,
            candidates=suggestions[:candidate_limit],
        )

    async def async_search_two_pass(
        self,
        query: str,
        async_scorer: AsyncJevScorer | None = None,
        repo_root: str | None = None,
        top_k: int | None = None,
        shortlist_size: int = 20,
        concurrency: int = 10,
    ) -> SearchSession:
        """Two-pass search: LocalScorer narrows, AsyncJevScorer re-scores in parallel."""
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
        scored: list[tuple[str, float, str]] = []

        for candidate in candidates:
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

        # --- Pass 2: parallel async Jev re-scoring ---
        jev = async_scorer or AsyncJevScorer()
        sem = asyncio.Semaphore(concurrency)
        results: list[SearchResult] = []
        suggestions: list[SearchCandidate] = []
        pass2_start = len(audit)

        async def _score_one(path: str, q: str, cont: str) -> tuple[str, str, float, dict[str, Any]]:
            async with sem:
                s = await jev.score(path, q, cont)
                telemetry: dict[str, Any] = {
                    "latency_ms": jev.last_latency_ms,
                    "cost": jev.last_cost,
                    "input_tokens": jev.last_input_tokens,
                }
                return path, cont, s, telemetry

        tasks = [_score_one(c, query, cont) for c, _, cont in shortlist]
        jev_results = await asyncio.gather(*tasks)

        jev_ranked = sorted(jev_results, key=lambda item: item[2], reverse=True)
        top_runner_up = jev_ranked[1][2] if len(jev_ranked) > 1 else 0.0

        for i, (candidate, content, score, telemetry) in enumerate(jev_results, start=1):
            decision = self.gate.decide(
                score,
                runner_up=top_runner_up if jev_ranked and jev_ranked[0][0] == candidate else 0.0,
            )
            if decision is GateDecision.ACCEPT:
                results.append(
                    SearchResult(
                        path=candidate,
                        score=score,
                        provider="jev-async",
                        reason="Accepted by Jev (async two-pass)",
                        excerpt=self._excerpt(content, query),
                    )
                )
            elif self._has_candidate_score(score):
                suggestions.append(
                    SearchCandidate(
                        path=candidate,
                        score=score,
                        provider="jev-async",
                        decision=decision.value,
                        reason=self._candidate_reason(decision),
                        excerpt=self._excerpt(content, query),
                    )
                )
            audit.append({
                "step": pass2_start + i,
                "provider": "jev-async",
                "score": score,
                "decision": decision.value,
                "path": candidate,
                **telemetry,
            })

        results.sort(key=lambda r: r.score, reverse=True)
        suggestions.sort(key=lambda r: r.score, reverse=True)
        limit = min(requested_top_k, len(results))
        candidate_limit = min(requested_top_k, len(suggestions))
        telemetry_summary = self._compute_telemetry(audit)

        return SearchSession(
            query=query,
            repo_root=active_root,
            results=results[:limit],
            audit_trail=audit,
            telemetry=telemetry_summary,
            candidates=suggestions[:candidate_limit],
        )
