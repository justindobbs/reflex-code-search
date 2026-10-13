# reflex-code-search Roadmap

**Status:** Draft direction, without delivery dates.

## Product direction

reflex-code-search is a lightweight, offline-first code search tool using a REFLEX-style control loop: fast bounded scoring, a three-way confidence gate, and optional escalation to a stronger scorer.

The project should stay narrow and explainable. Improvements should raise recall and developer ergonomics without growing the tool into an agent runtime, IDE plugin, or broad framework.

## Current starting point

The repository has a working CLI and library API at v0.1.0:

- **LocalScorer** (offline): 60% recall on own repo, 100% on tracecore-reflex. Fast, zero cost.
- **JevScorer** (live): 83% recall on own repo, 100% on tracecore-reflex. ~15s per query, ~$0.0005/query.
- **Fallback**: `default_fallback_scorer` uses simple term overlap — same blind spots as LocalScorer.
- **Tests**: 49 passing, ruff clean, CI on Python 3.11–3.13.
- **Benchmarks**: 18 hand-labelled queries across 2 repos.

Key gaps:

- LocalScorer misses conceptual queries where exact terms don't appear in path or content.
- Fallback can't resolve uncertain cases that LocalScorer already missed (same algorithm).
- No aggregate session telemetry (total cost, latency, decision counts).
- Live mode calls the API for every file — impractical for repos with 100+ files.

## Roadmap

### 1. Improve LocalScorer recall

Raise offline recall on reflex-code-search from 60% to ≥75% without API calls.

- Add synonym/alias expansion — a small hardcoded map (~30–50 entries) of conceptual synonyms. Expand query terms before scoring. Keep the map in `scorers.py` as a module constant.
- Add docstring boosting — extract the first docstring from Python files and weight it separately (10% weight, taken from content weight). Docstrings often describe a file's purpose in terms that match conceptual queries.
- Increase content preview from 4000 to 8000 chars.
- Re-run benchmarks on the full 18-query dataset. If any tracecore-reflex queries regress, tune weights.

**Exit evidence:** LocalScorer recall ≥75% on reflex-code-search queries, maintained 100% on tracecore-reflex. Existing tests pass. No new dependencies. Benchmarks updated.

### 2. Smart Jev fallback

Use Jev only for uncertain candidates, not every file. This is the core REFLEX escalation pattern.

- Add a `JevFallback` class in `fallback.py` that conforms to the existing fallback signature and internally calls `JevScorer`. Records telemetry (latency, cost, tokens) on the instance.
- Add CLI `--smart-fallback` flag — uses `JevFallback` instead of `default_fallback_scorer`. Requires `OPENROUTER_API_KEY`. Mutually exclusive with `--with-fallback`.
- When fallback is a `JevFallback`, include its telemetry in the audit trail step.

**Exit evidence:** Higher recall than `--with-fallback` on the benchmark dataset. Fewer API calls than `--live` (only uncertain files scored). Benchmarks updated.

### 3. Session-level telemetry

Aggregate per-step telemetry into a session summary, like tracecore-reflex's `EpisodeTelemetry`.

- Add a `SessionTelemetry` dataclass in `models.py` with counts for files scanned, accepted, uncertain, rejected, fallback calls, total latency, cost, and tokens.
- Attach to `SearchSession` — computed from the audit trail at the end of `search()`.
- Add CLI `--stats` flag that prints a one-line summary after results.
- Include telemetry block in `--json` output.

**Exit evidence:** Telemetry counts match audit trail for local, fallback, and mixed scenarios. JSON output includes telemetry. `--stats` prints the summary line.

### 4. Pre-filter for live mode

Make `--live` practical for larger repos by scoring only a shortlist with Jev.

- Add two-pass search in `searcher.py`: Pass 1 uses LocalScorer on all files, keeps top N (configurable, default 20). Pass 2 re-scores the shortlist with JevScorer.
- `--live` uses the two-pass approach by default. `--live-all` preserves the old behavior for benchmarking or small repos.
- New CLI option `--shortlist N` controls the shortlist size.

**Exit evidence:** Recall within 5% of full-live on the benchmark dataset. Latency and cost proportional to shortlist size, not total file count. Benchmarks updated.

### 5. Expand benchmark dataset

Broader coverage for measuring scorer improvements.

- Add 10+ queries to `benchmarks/queries.json` — conceptual queries, cross-file queries, config/data queries.
- Add a third benchmark repo (a small, well-known public Python project, 30–80 files).
- Update `docs/benchmarks.md` with full results after phases 1–4.

**Exit evidence:** Benchmark dataset covers the query types that drive scorer development. Results are reproducible via `tools/bench.py`.

## Implementation order

| Phase | Effort | Depends on | Key deliverable |
|-------|--------|------------|-----------------|
| 1     | ~1 session | — | Higher offline recall |
| 2     | ~1 session | — | Smart Jev fallback |
| 3     | ~0.5 session | — | Session telemetry |
| 4     | ~1 session | Phase 2 | Scalable live mode |
| 5     | ~0.5 session | Phases 1–4 | Broader benchmarks |

Phases 1–3 are independent. Phase 4 depends on Phase 2. Phase 5 comes last.

## Design constraints (do not violate)

From `docs/release-spec.md` and `docs/architecture.md`:

- No symbolic code graph or tree-sitter parsing
- No multi-agent orchestration
- No IDE integration layer
- No broad plugin system beyond the existing `Scorer` protocol
- No runtime dependency on tracecore-reflex (port patterns, don't import)
- Keep dependencies minimal (stdlib + httpx + pathspec + typer + dotenv)
- Stay testable with local heuristics by default

## Scope discipline

The central deliverable is a narrow, reliable code search primitive. New features should improve recall, scoring quality, or developer ergonomics without growing the tool beyond its stated purpose.
