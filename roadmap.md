# reflex-code-search Roadmap

**Status:** Working direction, without delivery dates. Public release is under
consideration; this roadmap does not imply that repository visibility has
changed.

## Product direction

Keep reflex-code-search a lightweight, offline-first tool for finding relevant
files in a codebase. Improve retrieval quality and make results predictable,
explainable, and easy to evaluate. Keep the optional Jev integration separate
from the local search path.

## Priorities

### 1. Prepare the project for possible public use

- Keep setup, supported Python versions, CLI examples, and development checks
  accurate across the README, contributing guide, and CI.
- Make the project scope, current limitations, and benchmark methodology clear
  to someone encountering the repository for the first time.
- Review repository metadata, tracked files, and Git history for anything that
  should not be published; confirm licensing and contribution guidance are
  clear before changing visibility.
- Decide on a simple issue and release process if the project is made public.

### 2. Improve retrieval using measured results

- Keep the benchmark suites for this project, tracecore-reflex, and pinned
  upstream Click 8.5.0 reproducible.
- Use precision@k, reciprocal rank, and missed-file reports to target changes.
  Current local recall at top_k=5 and threshold=0.3 is 85% on this project,
  94% on tracecore-reflex, and 100% on Click.
- Evaluate ranking changes across every suite and retain the deterministic,
  dependency-light local search path.

### 3. Keep installation and maintenance dependable

- Maintain CI coverage for supported Python versions, tests, lint, wheel build,
  and an installed-CLI smoke check.
- Keep release notes, architecture documentation, and benchmark results aligned
  with shipped behavior.
- Document optional live scoring requirements and costs without making them a
  prerequisite for local use.

## Current capabilities

- Offline `LocalScorer` with synonym expansion, docstring and definition
  matching, and phrase scoring.
- Optional Jev scoring, uncertain-case fallback, and two-pass live search.
- Three-way confidence gate, audit trail, and per-search telemetry.
- Repository discovery with nested `.gitignore` support.
- CLI and library interfaces, with tests and Python 3.11–3.13 CI.

## Out of scope

- Symbolic code graphs or tree-sitter parsing.
- IDE integration or a repository hosting platform.
- A broad plugin system beyond the existing `Scorer` protocol.
- Runtime dependency on tracecore-reflex.
