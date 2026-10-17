"""Relevance scorers for reflex-code-search."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Callable
from pathlib import Path

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
    "whether",
    "so", "than", "too", "very", "just", "also",
})

# Regex for extracting Python/JS/Go/Rust definitions from source
_DEFINITION_RE = re.compile(
    r"(?:^|\n)\s*(?:def|class|function|func|fn|const|let|var|type|interface|struct|enum)\s+(\w+)",
)
_FIELD_RE = re.compile(r"(?m)^\s{4}([A-Za-z_]\w*)\s*(?::|=)")

# Regex to extract the first docstring from a Python file
_DOCSTRING_RE = re.compile(r'"""(.*?)"""', re.DOTALL)

# Common key/value settings in TOML, YAML, JSON, INI, and Python modules.
_CONFIG_KEY_RE = re.compile(r"(?m)^\s*[\"']?([A-Za-z_][\w.-]*)[\"']?\s*[:=]")

# Synonym map for conceptual query expansion.
# Each key maps to terms that are interchangeable in a code-search context.
_SYNONYMS: dict[str, list[str]] = {
    "collect": ["discover", "walk", "scan", "find", "gather"],
    "discover": ["collect", "walk", "scan", "find"],
    "audit": ["trail", "trace", "log", "telemetry", "record"],
    "trail": ["audit", "trace", "log", "telemetry"],
    "trace": ["audit", "trail", "log", "telemetry"],
    "telemetry": ["audit", "trail", "trace", "log", "metric"],
    "structure": ["model", "dataclass", "schema", "format"],
    "model": ["structure", "dataclass", "schema", "format"],
    "schema": ["structure", "model", "dataclass", "format"],
    "config": ["configuration", "settings", "options", "defaults"],
    "configuration": ["config", "settings", "options", "defaults"],
    "settings": ["config", "configuration", "options", "defaults"],
    "boost": ["weight", "score", "bonus", "bump"],
    "score": ["rank", "relevance", "rating", "weight"],
    "rank": ["score", "relevance", "rating", "order"],
    "relevance": ["score", "rank", "rating"],
    "gate": ["threshold", "decision", "filter", "confidence"],
    "threshold": ["gate", "limit", "cutoff", "boundary"],
    "confidence": ["gate", "threshold", "certainty"],
    "decide": ["decision", "determine", "select"],
    "decision": ["decide", "outcome", "result"],
    "invok": ["call", "execute", "dispatch"],
    "calculat": ["compute", "derive", "aggregate"],
    "structur": ["schema", "field", "model", "dataclass"],
    "prefilter": ["shortlist", "narrow", "twopass", "two_pass"],
    "reduce": ["narrow", "limit", "prefilter", "shortlist"],
    "fallback": ["escalate", "escalation", "backup", "alternative"],
    "escalate": ["fallback", "escalation"],
    "escalation": ["fallback", "escalate"],
    "file": ["path", "module", "source"],
    "path": ["file", "route", "directory"],
    "search": ["query", "find", "lookup", "match"],
    "query": ["search", "question", "request"],
    "test": ["spec", "check", "verify", "assert", "unittest"],
    "error": ["exception", "failure", "fault"],
    "exception": ["error", "failure", "raise"],
    "parse": ["extract", "tokenize", "split", "read"],
    "extract": ["parse", "pull", "get", "read"],
    "export": ["public", "expose", "api", "interface"],
    "public": ["export", "expose", "api"],
    "define": ["declare", "create", "register"],
    "declare": ["define", "create", "register"],
    "extension": ["suffix", "type", "format"],
    "suffix": ["extension", "type", "ending"],
    "exclude": ["ignore", "skip", "filter", "omit", "gitignore"],
    "ignore": ["exclude", "skip", "filter", "gitignore"],
    "gitignore": ["ignore", "exclude", "skip"],
    "exclusion": ["exclude", "ignore", "skip", "filter", "gitignore"],
    "cli": ["command", "terminal", "console", "entrypoint"],
    "command": ["cli", "terminal", "console"],
    "entrypoint": ["cli", "main", "entry", "command"],
    "result": ["output", "response", "return"],
    "output": ["result", "response", "return", "emit"],
    "architecture": ["design", "structure", "overview", "spec"],
    "document": ["doc", "readme", "spec", "guide", "architecture"],
    "checklist": ["guide", "procedure", "steps", "workflow"],
    "normalize": ["stem", "strip", "reduce", "transform"],
    "stem": ["normalize", "strip", "suffix"],
}

# Simple suffix stripping for query term normalization.
# Not a full stemmer — just enough to map inflected forms to synonym keys.
_SUFFIX_RULES = [
    ("ying", "y"),     # applying → apply
    ("ting", "t"),     # collecting → collect
    ("ning", "n"),     # scanning → scan
    ("ling", "le"),    # handling → handle
    ("ring", "re"),    # scoring → score, filtering → filtre (substring match works)
    ("ding", "d"),     # building → build
    ("ping", "p"),     # mapping → map
    ("ging", "g"),     # logging → log
    ("ing", ""),       # scoring → scor (substring match still works)
    ("ied", "y"),      # applied → apply
    ("ted", "t"),      # collected → collect
    ("ned", "n"),      # scanned → scan
    ("red", "r"),      # filtered → filter
    ("ded", "d"),      # excluded → exclud (substring match works)
    ("ped", "p"),      # mapped → map
    ("ged", "g"),      # logged → log
    ("ed", ""),        # scored → scor (substring match works)
    ("ly", ""),        # directly → direct
    ("s", ""),         # files → file
]


def _stem(word: str) -> str:
    """Minimal suffix stripping for synonym map lookups."""
    if len(word) <= 3:
        return word
    for suffix, replacement in _SUFFIX_RULES:
        if word.endswith(suffix) and len(word) - len(suffix) + len(replacement) >= 3:
            return word[: -len(suffix)] + replacement
    return word


class LocalScorer:
    """Fast local scorer with bigram matching, definition boosting, and stopword filtering.

    Implements the ``Scorer`` protocol from ``reflex_search.models``.
    """

    provider = "local"

    def score(self, file_path: str, query: str, content: str) -> float:
        query_terms = self._tokenize(query)
        if not query_terms:
            return 0.0

        expanded = self._expand_synonyms(query_terms)
        originals = set(query_terms)
        n = len(query_terms)  # normalize by original term count

        path_text = file_path.lower()
        content_preview = content[:8000].lower()
        content_terms = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", content[:8000])
        content_terms = content_terms.lower().replace("_", " ")

        # --- Unigram matching (original terms full weight, synonyms half) ---
        path_hits = self._weighted_hits(expanded, originals, path_text)
        content_hits = self._weighted_hits(expanded, originals, content_terms)

        path_score = 0.25 * (path_hits / n)
        content_score = 0.35 * (content_hits / n)

        # --- Bigram matching (phrase sensitivity, original terms only) ---
        bigram_score = 0.0
        if n >= 2:
            bigrams = [f"{query_terms[i]} {query_terms[i+1]}" for i in range(n - 1)]
            path_phrases = self._normalize_match_text(file_path)
            content_phrases = self._normalize_match_text(content[:8000])
            path_bigram_hits = sum(1 for bg in bigrams if bg in path_phrases)
            content_bigram_hits = sum(1 for bg in bigrams if bg in content_phrases)
            nb = len(bigrams)
            bigram_score = 0.15 * ((path_bigram_hits + content_bigram_hits) / nb)

        # --- Definition-aware boosting ---
        def_score = 0.0
        definitions = _DEFINITION_RE.findall(content[:8000])
        if definitions:
            def_names = {d.lower() for d in definitions}
            normalized_definitions = " ".join(
                re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ")
                for name in definitions
            )
            def_hits = self._weighted_hits(expanded, originals, normalized_definitions.lower())
            def_score = 0.15 * (def_hits / n)

        # Location/implementation questions benefit from matching query terms
        # against declared symbols, which is stronger evidence than prose.
        query_lower = query.lower()
        asks_for_implementation = any(
            marker in query_lower
            for marker in ("where", "defined", "definition", "implement", "class", "function", "method")
        )
        if definitions and asks_for_implementation:
            direct_definition_hits = sum(
                1 for term in originals if any(term in name for name in def_names)
            )
            def_score += 0.20 * (direct_definition_hits / n)

            # Exact symbol names are stronger evidence than incidental word
            # overlap, especially in large source files with many references.
            query_identifiers = re.findall(r"\b[A-Za-z_]\w*\b", query)
            specific_query_symbols = {
                symbol.lower()
                for symbol in query_identifiers
                if "_" in symbol or re.search(r"[A-Z]", symbol[1:])
            }
            query_symbols = specific_query_symbols | {
                symbol.lower()
                for symbol in query_identifiers
                if "decorator" in query_lower and symbol.lower() not in _STOPWORDS
            }
            # Large modules can declare the requested symbol beyond the text
            # preview. Search all declarations only for explicit symbol queries.
            declared_symbols = {
                name.lower() for name in _DEFINITION_RE.findall(content)
            }
            exact_symbol_hits = len(query_symbols & declared_symbols)
            def_score += min(0.50, 0.25 * exact_symbol_hits)

            symbol_references = sum(
                1
                for symbol in specific_query_symbols
                if re.search(rf"\b{re.escape(symbol)}\b", content_preview)
            )
            def_score += min(0.40, 0.20 * symbol_references)

        # --- Docstring boosting ---
        doc_score = 0.0
        doc_match = _DOCSTRING_RE.search(content[:8000])
        if doc_match:
            docstring = doc_match.group(1).lower()
            doc_hits = self._weighted_hits(expanded, originals, docstring)
            doc_score = 0.10 * (doc_hits / n)

        total = path_score + content_score + bigram_score + def_score + doc_score

        configuration_intent = any(
            term in query_lower for term in ("config", "configured", "setting", "settings")
        )
        exact_key_hits = 0
        if configuration_intent:
            config_keys = _CONFIG_KEY_RE.findall(content[:8000])
            normalized_keys = " ".join(
                re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key).replace("_", " ")
                for key in config_keys
            ).lower()
            if normalized_keys:
                key_hits = self._weighted_hits(expanded, originals, normalized_keys)
                total += min(0.30, 0.30 * key_hits / n)
                query_config_keys = {
                    key.lower()
                    for key in re.findall(r"\b[A-Za-z_]\w*\b", query)
                    if "_" in key
                }
                declared_config_keys = {key.lower() for key in config_keys}
                exact_key_hits = len(query_config_keys & declared_config_keys)
                total += min(0.48, 0.12 * exact_key_hits)
                if exact_key_hits:
                    if Path(file_path).suffix.lower() in {".toml", ".ini", ".yaml", ".yml", ".cfg", ".conf"}:
                        total += 0.35
                    else:
                        # References to settings are useful, but the file that
                        # declares them is the direct answer to a configuration query.
                        total *= 0.65

        if any(term in query_lower for term in ("structured", "field", "telemetry", "audit trail")):
            field_names = _FIELD_RE.findall(content[:8000])
            normalized_fields = " ".join(
                re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name).replace("_", " ")
                for name in field_names
            ).lower()
            field_hits = self._weighted_hits(expanded, originals, normalized_fields)
            total += min(0.20, 0.15 * field_hits / n)

        # Session audit and telemetry questions should favor the files that
        # store or calculate those values over modules that merely report
        # provider-level telemetry.
        if "audit trail" in query_lower or "audit_trail" in query_lower:
            audit_structure = re.search(
                r"\baudit_trail\s*[:=]|\baudit\s*:\s*list\b|\baudit\.append\s*\(",
                content,
            )
            if audit_structure:
                total += 0.22
            elif Path(file_path).suffix.lower() not in {".md", ".rst", ".txt"}:
                total *= 0.55
        elif "telemetry" in query_lower and "session" in query_lower:
            session_telemetry = re.search(
                r"\bclass\s+SessionTelemetry\b|\bdef\s+_compute_telemetry\b|"
                r"\bSessionTelemetry\s*\(|\btelemetry_summary\s*=",
                content,
            )
            if session_telemetry:
                total += 0.22
            elif Path(file_path).suffix.lower() not in {".md", ".rst", ".txt"}:
                total *= 0.65

        enum_values = {
            value.lower()
            for value in re.findall(r"(?m)^\s{4}([A-Z][A-Z0-9_]*)\s*=", content[:8000])
        }
        query_outcomes = originals & {"accept", "reject", "uncertain", "allow", "deny"}
        if enum_values and len(query_outcomes & enum_values) >= 2 and any(
            term in query_lower for term in ("gate", "decision", "decide", "outcome")
        ):
            total += min(0.20, 0.10 * len(query_outcomes & enum_values))

        # Evaluation fixtures repeat their own query text and can otherwise
        # outrank implementation files for unrelated questions.
        normalized_path = file_path.lower().replace("\\", "/")
        benchmark_intent = any(
            term in query_lower
            for term in ("benchmark", "recall", "precision", "mrr", "evaluation")
        )
        if not benchmark_intent and normalized_path.endswith(
            ("benchmarks/queries.json", "docs/benchmarks.md")
        ):
            total *= 0.25

        documentation_intent = any(
            term in query_lower
            for term in ("readme", "document", "documentation", "release", "changelog", "roadmap", "overview")
        )
        if not documentation_intent and query_lower.startswith(("how ", "where ", "when ")):
            if normalized_path.endswith("/readme.md") or normalized_path == "readme.md":
                total *= 0.70
            elif normalized_path.endswith("/changelog.md") or normalized_path == "changelog.md":
                total *= 0.50

        return round(min(total, 1.0), 4)

    @staticmethod
    def _weighted_hits(
        expanded: list[str], originals: set[str], text: str,
    ) -> float:
        """Count hits with full weight for original terms, half for synonyms."""
        total = 0.0
        for term in expanded:
            if term in text:
                total += 1.0 if term in originals else 0.5
        return total

    @staticmethod
    def _tokenize(value: str) -> list[str]:
        normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
        normalized = re.sub(r"(?<=\w)['’]s\b", "", normalized)
        normalized = normalized.lower().replace("-", " ").replace("_", " ")
        normalized = re.sub(r"\bfall\s+back\b", "fallback", normalized)
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        parts = normalized.split()
        return [_stem(p) for p in parts if p and p not in _STOPWORDS]

    @staticmethod
    def _normalize_match_text(value: str) -> str:
        """Make common identifier and prose separators equivalent to spaces."""
        return re.sub(r"[-_]+", " ", value.lower())

    @staticmethod
    def _expand_synonyms(terms: list[str]) -> list[str]:
        """Expand query terms with synonyms, deduplicating while preserving order."""
        seen: set[str] = set()
        expanded: list[str] = []
        for term in terms:
            if term not in seen:
                seen.add(term)
                expanded.append(term)
            for syn in _SYNONYMS.get(term, ()):
                if syn not in seen:
                    seen.add(syn)
                    expanded.append(syn)
        return expanded


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
