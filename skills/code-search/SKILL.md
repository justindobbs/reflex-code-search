---
name: code-search
description: Search a codebase for files relevant to a natural-language question using reflex-code-search. Use this when you need to find which files contain the implementation, definition, or configuration that answers a question about a repository.
---

# Code Search Skill

Find relevant files in a codebase by running the `reflex-search` CLI.

## When to use

- You need to locate which files implement a feature, define a class, or configure a setting.
- You want ranked results with scores, not just filename matches.
- The repository is local on disk.

## Prerequisites

- `reflex-code-search` installed (`pip install -e .` from the repo root, or `pip install reflex-code-search`).
- For Jev-backed modes (`--smart-fallback`, `--live`, `--async`), set `OPENROUTER_API_KEY` in the environment or a `.env` file.

## Basic usage

```bash
reflex-search "<query>" <repo_root> --json
```

**Arguments:**
- `<query>` — Natural-language question (e.g. `"Where is the confidence gate defined?"`)
- `<repo_root>` — Path to the repository root (defaults to `.`)

**Common options:**
- `--top-k N` — Max files to return (default 5)
- `--threshold F` — Accept threshold (default 0.65; use 0.30 for broader results)
- `--json` — Emit structured JSON output

## Examples

### Local search (fast, offline)

```bash
reflex-search "How does authentication work?" ./my-repo --json --threshold 0.30
```

### Smart fallback (local + Jev for uncertain candidates)

```bash
reflex-search "Where are streaming responses handled?" ./my-repo --smart-fallback --json --threshold 0.30
```

### Async smart fallback (parallel Jev calls)

```bash
reflex-search "Where are streaming responses handled?" ./my-repo --smart-fallback --async --json --threshold 0.30
```

### Two-pass live mode (LocalScorer shortlists, Jev re-scores)

```bash
reflex-search "How does the transport layer work?" ./my-repo --live --shortlist 20 --json --threshold 0.30
```

### Async two-pass (parallel Jev re-scoring)

```bash
reflex-search "How does the transport layer work?" ./my-repo --live --async --shortlist 20 --json --threshold 0.30
```

## JSON output shape

```json
{
  "query": "Where is the confidence gate defined?",
  "repo_root": "/path/to/repo",
  "results": [
    {
      "path": "reflex_search/gate.py",
      "score": 0.85,
      "provider": "local",
      "reason": "Accepted by confidence gate",
      "excerpt": "class ConfidenceGate:\n    ..."
    }
  ],
  "audit_trail": [ ... ],
  "telemetry": {
    "files_scanned": 12,
    "accepted": 2,
    "uncertain": 3,
    "rejected": 7,
    "fallback_calls": 0,
    "total_latency_ms": 45.0,
    "total_cost": 0.0,
    "total_tokens": 0
  }
}
```

## Edge cases

- **Missing API key:** `--smart-fallback`, `--live`, and `--async` modes fall back to local scoring silently if `OPENROUTER_API_KEY` is not set.
- **Large repos:** Local scoring is fast (~100ms for 30 files). For repos with hundreds of files, use `--live --shortlist 20` to limit Jev calls.
- **Threshold tuning:** Default 0.65 is strict. Use 0.30 for exploratory searches. Use `--stats` to see how many files were accepted/rejected.
- **No results:** Lower `--threshold` or broaden the query. Add `--verbose` to inspect the full audit trail.

## Additional flags

| Flag | Description |
|------|-------------|
| `--verbose` | Print the full audit trail |
| `--stats` | Print a one-line telemetry summary |
| `--uncertain F` | Uncertain threshold (default 0.40) |
| `--min-margin F` | Minimum score margin for accept |
| `--with-fallback` | Use simple term-overlap fallback |
| `--live-all` | Score every file with Jev (expensive) |
