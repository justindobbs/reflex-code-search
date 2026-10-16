# reflex-code-search Roadmap

**Status:** Working direction, without delivery dates.

## Product direction

Keep reflex-code-search a lightweight, offline-first file search tool. Prioritize
retrieval quality, trustworthy results and telemetry, and predictable CLI
behavior. Avoid expanding into an agent runtime, IDE, or repository platform.

## Current capabilities

- Offline `LocalScorer` with synonym expansion, docstring and definition
  matching, and phrase scoring.
- Optional Jev scoring, uncertain-case fallback, and two-pass live search.
- Three-way confidence gate, audit trail, and per-search telemetry.
- Repository discovery with nested `.gitignore` support.
- CLI and library interfaces, with tests and Python 3.11–3.13 CI.

## Next work

### 1. Make retrieval evaluation more useful

- The harness now reports precision@k and reciprocal rank, and the query set
  includes more conceptual and cross-file questions.
- Keep benchmark reports refreshed with measured results and missed files.
- Add an independently maintained repository; current suites cover this
  project and its related sibling only.
- Preserve the local benchmark as a regression check when scorer behavior changes.

### 2. Improve offline retrieval based on evidence

- Current local recall is 85% on this project and 94% on tracecore-reflex
  (top_k=5, threshold=0.3); use the listed misses to guide retrieval work.
- Evaluate changes against all benchmark suites and check for regressions.
- Keep the scorer deterministic, local, dependency-light, and explainable.

### 3. Harden the release path

- CI now builds and installs a wheel, then checks the installed CLI.
- Keep release notes, architecture docs, and benchmark numbers aligned with the
  implementation.

## Design constraints

- No symbolic code graph or tree-sitter parsing.
- No multi-agent orchestration or IDE integration.
- No broad plugin system beyond the existing `Scorer` protocol.
- No runtime dependency on tracecore-reflex.
- Keep dependencies minimal and local search usable without API credentials.
