"""Core REFLEX-style search logic."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


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
}


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


class JevClient:
    """A thin relevance scorer.

    Without a remote API key, it falls back to a local heuristic that is deterministic,
    cheap, and good enough for repository-level narrowing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.endpoint = endpoint or os.getenv("JEV_ENDPOINT")

    def score_relevance(self, file_path: str, query: str, content: str) -> float:
        """Return a 0-1 relevance score for a candidate file."""
        if self.api_key and self.endpoint:
            return self._remote_score(file_path, query, content)
        return self._local_score(file_path, query, content)

    def _local_score(self, file_path: str, query: str, content: str) -> float:
        query_terms = self._tokenize(query)
        path_text = file_path.lower()
        content_preview = content[:2000].lower()

        if not query_terms:
            return 0.0

        score = 0.0
        for term in query_terms:
            if term in path_text:
                score += 0.35
            if term in content_preview:
                score += 0.65 / max(len(query_terms), 1)

        # Mixture of path overlap and content overlap
        score = min(score, 1.0)
        return round(score, 4)

    def _remote_score(self, file_path: str, query: str, content: str) -> float:
        """Optional remote call. Kept simple so the library remains testable.

        In a real deployment this could POST a payload to a Jev-compatible endpoint.
        """
        del file_path, query, content
        return 0.5

    @staticmethod
    def _tokenize(value: str) -> list[str]:
        return [part for part in value.lower().replace("-", " ").split() if part]


class ConfidenceGate:
    """Simple gating logic for a REFLEX search loop."""

    def __init__(self, threshold: float = 0.65, min_margin: float = 0.1) -> None:
        self.threshold = threshold
        self.min_margin = min_margin

    def should_accept(self, score: float, alternative_score: float = 0.0) -> bool:
        if score < self.threshold:
            return False
        if score - alternative_score < self.min_margin:
            return False
        return True


class ReflexCodeSearcher:
    """Minimal semantic code search using a REFLEX-style loop."""

    def __init__(
        self,
        repo_root: str | None = None,
        jev_client: JevClient | None = None,
        llm_fallback: Callable[[str, str, str], float] | None = None,
        threshold: float = 0.65,
        top_k: int = 5,
    ) -> None:
        self.repo_root = repo_root or os.getcwd()
        self.jev_client = jev_client or JevClient()
        self.llm_fallback = llm_fallback
        self.threshold = threshold
        self.top_k = top_k
        self.gate = ConfidenceGate(threshold=threshold)

    def search(self, query: str, repo_root: str | None = None, top_k: int | None = None) -> SearchSession:
        repo_root = repo_root or self.repo_root
        candidates = self._collect_files(repo_root)
        results: list[SearchResult] = []
        audit: list[dict[str, Any]] = []

        for index, candidate in enumerate(candidates, start=1):
            try:
                content = self._read_file(candidate)
            except OSError:
                continue

            score = self.jev_client.score_relevance(candidate, query, content)
            decision = "accept" if self.gate.should_accept(score) else "skip"

            if score >= self.threshold:
                provider = "jev"
                reason = "Strong relevance score"
                results.append(
                    SearchResult(
                        path=candidate,
                        score=score,
                        provider=provider,
                        reason=reason,
                        excerpt=self._excerpt(content, query),
                    )
                )
                audit.append({
                    "step": index,
                    "provider": provider,
                    "score": score,
                    "decision": decision,
                    "path": candidate,
                })
                continue

            # Optional fallback for uncertain cases
            if self.llm_fallback is not None:
                llm_score = self.llm_fallback(candidate, query, content)
                if llm_score >= self.threshold:
                    results.append(
                        SearchResult(
                            path=candidate,
                            score=llm_score,
                            provider="llm_fallback",
                            reason="LLM fallback accepted this candidate",
                            excerpt=self._excerpt(content, query),
                        )
                    )
                    audit.append({
                        "step": index,
                        "provider": "llm_fallback",
                        "score": llm_score,
                        "decision": "accept",
                        "path": candidate,
                    })
                    continue

                audit.append({
                    "step": index,
                    "provider": "llm_fallback",
                    "score": llm_score,
                    "decision": "skip",
                    "path": candidate,
                })
                continue

            audit.append({
                "step": index,
                "provider": "jev",
                "score": score,
                "decision": decision,
                "path": candidate,
            })

        results.sort(key=lambda item: item.score, reverse=True)
        top_n = min(top_k or self.top_k, len(results))

        return SearchSession(
            query=query,
            repo_root=repo_root,
            results=results[:top_n],
            audit_trail=audit,
        )

    def _collect_files(self, repo_root: str) -> list[str]:
        root = Path(repo_root)
        files: list[str] = []

        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in DEFAULT_EXCLUDES for part in path.parts):
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

    def _read_file(self, relative_path: str) -> str:
        path = Path(self.repo_root) / relative_path
        return path.read_text(encoding="utf-8", errors="ignore")

    def _excerpt(self, content: str, query: str) -> str:
        query_terms = [t.lower() for t in query.replace("-", " ").split() if t]
        lines = content.splitlines()
        prefix: list[str] = []

        for line in lines:
            lowered = line.lower()
            if any(term in lowered for term in query_terms):
                prefix.append(line.strip())
                if len(prefix) >= 3:
                    break

        if not prefix:
            excerpt = "\n".join(lines[:3])
        else:
            excerpt = "\n".join(prefix)

        return excerpt[:400]


def _default_llm_fallback(path: str, query: str, content: str) -> float:
    """Simple fallback heuristic used when a real model is not configured.

    It is intentionally conservative; the fallback only returns a positive score when the
    file clearly matches the query.
    """
    query_terms = [part.lower() for part in query.replace("-", " ").split() if part]
    text = f"{path} {content}".lower()
    matches = sum(1 for term in query_terms if term in text)
    if not query_terms:
        return 0.0
    score = matches / len(query_terms)
    return min(score, 0.9)
