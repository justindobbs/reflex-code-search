# Changelog

## Unreleased

### Documentation

- Add landing-page use cases and an illustrative search-flow visual.
- Add a security policy covering vulnerability reporting and optional live-scoring data handling.

## 0.1.0 — 2026-10-03

Initial release.

### Features

- **LocalScorer** — fast term-overlap heuristic for offline file ranking (30% path, 70% content)
- **JevScorer** — live relevance scoring via the Jev Decisions API (OpenRouter), with automatic fallback to LocalScorer on errors
- **ConfidenceGate** — three-way gate (accept / uncertain / reject) with configurable thresholds and `min_margin` check ported from tracecore-reflex
- **Fallback path** — optional fallback scorer for uncertain candidates, invoked only when configured
- **Audit trail** — per-step telemetry including provider, score, decision, latency, cost, and token count
- **CLI** — `reflex-search` command with `--live`, `--json`, `--verbose`, `--with-fallback`, `--min-margin`, `--threshold`, `--uncertain`, `--top-k`
- **Library API** — `ReflexCodeSearcher`, `LocalScorer`, `JevScorer`, `ConfidenceGate`, `Scorer` protocol
- **python-dotenv** — automatic `.env` loading in the CLI


