# reflex-code-search Roadmap

**Status:** Working direction, without delivery dates.

## Product direction

Keep reflex-code-search a lightweight, offline-first tool for finding relevant
files in a codebase. Improve retrieval quality and make results predictable,
explainable, and easy to evaluate. Keep the optional Jev integration separate
from the local search path.

## Current baseline

- 60 queries across 4 repos (reflex-code-search, tracecore-reflex, Click 8.5.0, httpx 0.28.1).
- LocalScorer: 100% recall on 3 repos, 81% on httpx. Jev closes all httpx gaps.
- Precision@k averages 24–29%.
- JevScorer is synchronous, ~500ms per file.
- CLI and library interfaces; no MCP or tool-calling integration.

## Phases

### 1. Measure Jev vs Local head-to-head

Show whether the REFLEX loop adds value beyond confirming local decisions.

- Add `--smart-fallback` mode to `bench.py` (Local scorer + Jev fallback for uncertain candidates).
- Record per-query: recall delta, MRR delta, fallback call count, cost, latency.
- Add fallback columns to `docs/benchmarks.md` alongside local results.
- Focus on httpx suite first (known gaps), then all suites.

**Exit evidence:** Side-by-side numbers showing where smart-fallback improves recall and ranking, and what it costs.

### 2. Improve precision

Reduce noise in the top-k so results are usable as agent context.

- Analyze false accepts: categorize by cause (common term overlap, synonym over-expansion, doc/test file leakage).
- Tighten scoring for common over-scorers: stronger demotion for test and doc files when queries ask about implementation.
- Consider dynamic top-k cutoff based on score gap from the top result.
- Add precision tracking to benchmark CI output.

**Exit evidence:** Precision@5 improves from ~27% toward 40%+ without recall regression.

### 3. Language-aware file understanding

Replace heuristic branches with lightweight AST extraction.

- Python first: use the `ast` module to extract class names, function signatures, docstrings, and imports (no new dependency).
- Replace `_DEFINITION_RE` and `_DOCSTRING_RE` regex for `.py` files with the AST pass; keep regex fallback for non-Python files.
- Evaluate tree-sitter as an optional dependency for multi-language support.

**Exit evidence:** Same or better recall/MRR on all suites, cleaner scorer code, extensible to new languages.

### 4. Async / parallel scoring

Cut live-mode latency for the two-pass shortlist.

- Add `AsyncJevScorer` implementing an async scorer variant.
- Add `async_search` and `async_search_two_pass` to `ReflexCodeSearcher` using `asyncio.gather`.
- Keep sync paths unchanged; add `--async` flag to CLI for live modes.

**Exit evidence:** 20-file shortlist from ~10s sequential to ~1–2s parallel.

### 5. MCP / tool integration

Expose the library as an MCP tool for agents.

- Define a `search_codebase` MCP tool (query, repo_root, top_k, threshold, live).
- Return structured results matching the existing `SearchSession` shape.
- Package as an optional MCP server entry point; keep MCP SDK as an optional dependency.

**Exit evidence:** An agent can call `search_codebase` and receive ranked files without importing reflex-code-search directly.

## Sequencing

Phases 1–2 are measurement and tuning — no new dependencies, low risk, high signal. Phase 3 is a refactor that benefits from 1–2 being done. Phases 4 and 5 are independent and can proceed in either order.

## Ongoing

- Keep setup, CI, and documentation accurate.
- Evaluate ranking changes across every suite before merging.
- Document optional live scoring requirements and costs without making them a prerequisite for local use.
