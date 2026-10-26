# reflex-code-search Roadmap

**Status:** Working direction, without delivery dates.

## Product direction

Keep reflex-code-search a lightweight, offline-first tool for finding relevant
files in a codebase. Improve retrieval quality and make results predictable,
explainable, and easy to evaluate. Keep the optional Jev integration separate
from the local search path. The primary agent workflow is: given a code question
or intended change, identify the smallest useful set of implementation, test,
configuration, and caller files to inspect first, with evidence for each choice.

## Current baseline

- 60 queries across 4 repos (reflex-code-search, tracecore-reflex, Click 8.5.0, httpx 0.28.1).
- LocalScorer: 98–100% recall on 3 repos, 88% on httpx. Jev closes remaining httpx gaps.
- Precision@k averages 24–29%.
- AST-based definition/docstring extraction for Python files (Phase 3).
- AsyncJevScorer with `asyncio.gather` and configurable concurrency (Phase 4).
- Agent Skills file and optional MCP server (Phase 5).
- 110 tests (105 passing, 5 skipped without optional mcp dependency), ruff clean.

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

### 3. Language-aware file understanding ✅

Replace heuristic branches with lightweight AST extraction.

- ✅ Python first: use the `ast` module to extract class names, function signatures, docstrings, and imports (no new dependency).
- ✅ Replace `_DEFINITION_RE` and `_DOCSTRING_RE` regex for `.py` files with the AST pass; keep regex fallback for non-Python files.
- Evaluate tree-sitter as an optional dependency for multi-language support.

**Exit evidence:** Benchmarks confirmed no recall regression (98%/100% unchanged). New `ast_extract.py` module with full test coverage.

### 4. Async / parallel scoring ✅

Cut live-mode latency for the two-pass shortlist.

- ✅ Add `AsyncJevScorer` implementing an async scorer variant.
- ✅ Add `async_search` and `async_search_two_pass` to `ReflexCodeSearcher` using `asyncio.gather`.
- ✅ Keep sync paths unchanged; add `--async` flag to CLI for live modes.

**Exit evidence:** `AsyncJevScorer`, `async_search`, `async_search_two_pass` with configurable `Semaphore(concurrency)`. CLI `--async` flag wired for `--live` and `--smart-fallback`. 14 async tests passing.

### 5. MCP / tool integration ✅

Expose the library as an MCP tool for agents.

- ✅ Agent Skills file at `skills/code-search/SKILL.md` (zero-dependency agent integration).
- ✅ Define a `search_codebase` MCP tool (query, repo_root, top_k, threshold, live, smart_fallback).
- ✅ Return structured results matching the existing `SearchSession` shape.
- ✅ Package as optional MCP server entry point (`reflex-search-mcp`); `mcp[cli]>=1.0` as optional dependency.

**Exit evidence:** MCP server runs via stdio transport. Import guard raises clear `ImportError` without the optional dep. 6 MCP tests (1 passes without mcp, 5 run when mcp is installed).

## Sequencing

Phases 1–5 are complete. Future work is tracked below.

## Ongoing

- Keep setup, CI, and documentation accurate.
- Evaluate ranking changes across every suite before merging.
- Document optional live scoring requirements and costs without making them a prerequisite for local use.

## Future direction: agent-oriented core search

Treat retrieval as a way to help an agent decide what to read before it edits
code. The core search tool should return useful, ranked file leads with enough
evidence for an agent to inspect them. Results are evidence-backed leads; a
confidence-gate decision does not claim that a result is verified correct.

The three-query repo-native context-pack pilot did not establish a coverage
gain and increased the inspected-file proxy on one task. Keep that presentation
experiment isolated while improving the core search workflow.

### 6. Benchmark real inspection tasks

Measure whether search helps an agent find the files it needs for realistic
repository questions and change requests.

- Add task-shaped queries such as “I need to change X; what should I inspect
  first?” across repositories and languages already represented in the project.
- Label relevant files by role where useful: implementation, test, configuration,
  caller, or documentation. Record reviewed relevance judgments so unlabelled
  results are not automatically treated as incorrect.
- Keep a held-out set for evaluating ranking changes. Compare the current search
  workflow with the existing baseline and, where practical, a simple `rg` workflow.
- Report top-k coverage, ranking quality, inspected-file count, excerpt/context
  size, latency, and optional API cost. Choose numeric targets after establishing
  this reviewed baseline.

**Exit evidence:** A reproducible benchmark report with reviewed judgments,
representative held-out tasks, and a clear account of when retrieval saves agent
inspection effort and when it does not.

### 7. Make ranking evidence visible

Give an agent enough information to judge why a file was returned and navigate
to the relevant code without implying that the score proves correctness.

- Return line-ranged excerpts tied to source locations.
- Keep accepted results separate from lower-confidence candidates, including
  each candidate's gate decision and supporting excerpt. ✅
- Explain contributing signals, such as path terms, content terms, phrases,
  definitions, and docstrings; keep the total score and gate decision separate
  from this evidence.
- Include scorer/provider and relevant configuration or version metadata so a
  result can be interpreted and reproduced.
- Keep an honest empty outcome when there is no positive retrieval signal.

**Exit evidence:** For every returned result, an agent can inspect the source
span and see the evidence behind its ranking. Repeated searches with the same
repository, scorer version, and configuration produce the same local ranking.

### 8. Improve core retrieval against observed failures

Improve the local ranking based on measured misses and false accepts from
realistic investigation tasks.

- Check whether task-style query wording dilutes useful technical terms.
- Improve symbol, path, definition, test, configuration, and caller signals
  only where reviewed misses show a need.
- Compare precision, coverage, and files inspected before and after each change.
- Keep the scorer local and deterministic; require evidence before adding
  persistent indexing or new retrieval dependencies.

**Exit evidence:** Changes improve held-out task coverage or reduce inspected
files without an unexplained precision regression.

### 9. Make agent adoption straightforward

Keep the same core search behavior available to people and agent runtimes.

- Document one quick path from installation to a local code search with
  no API key or external service.
- Keep CLI, library, MCP, and skill instructions aligned with the same result
  fields and uncertainty semantics.
- Provide concise setup and example prompts for supported agent integrations,
  including the correct skill discovery location for each platform.
- Make optional external scoring explicit and report when it was used.

**Exit evidence:** A new user can install the tool, run a local search, and
understand its result format without configuring remote services. Agent
integrations produce equivalent core results for the same query and options.

### 10. Evaluate advanced retrieval only against observed gaps

Treat embeddings, incremental indexes, broader AST support, and graph-based
signals as experiments rather than prerequisites for the core workflow.

- Select one retrieval improvement at a time based on failures in the reviewed
  benchmark.
- Compare quality, latency, resource use, setup cost, and operational complexity
  with the local baseline.
- Add persistent indexing only if measured repository sizes or search latency
  justify its maintenance and cache-invalidation costs.
- Keep all additional retrieval paths optional until they demonstrate a clear
  benefit for the target workflow.

**Exit evidence:** Each advanced component has a benchmarked improvement on
known failure cases, no unexplained regression on held-out tasks, and documented
costs and setup requirements.
