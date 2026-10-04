# reflex-code-search release spec

## Goal

Create a narrow, useful search tool for code repositories using a REFLEX-style control loop:

- start with fast bounded relevance checks
- escalate uncertain cases to an optional stronger fallback
- return the best matching files with a compact audit trail
- keep the implementation small and explainable

## Non-goals

This project intentionally does not include:

- IDE features
- broad repository knowledge graphs
- multi-agent orchestration
- PR review automation
- issue tracking integration
- code generation workflows
- deep semantic understanding beyond file-level relevance ranking

## Problem

When a developer asks a repo question like:

> "Where is authentication checked before a request reaches the handler?"

they usually do not want a general-purpose coding agent. They want the most plausible files to inspect next.

The tool should help answer that with a small, bounded control loop rather than by sending a huge amount of context to a model.

## User-facing behavior

### CLI

```bash
reflex-search "How is authentication checked before requests reach the handler?" .
```

Output should include:

- query
- repository root
- ordered result list
- each result with:
  - file path
  - score
  - provider (`local`, `jev`, or `fallback`)
  - short reason
  - short excerpt

Optional JSON mode:

```bash
reflex-search "Where are migrations defined?" . --json
```

### Library API

```python
from reflex_search import ReflexCodeSearcher

searcher = ReflexCodeSearcher(repo_root=".")
session = searcher.search("Where are migrations defined?")

for result in session.results:
    print(result.path, result.score, result.provider)
```

## Core design

### Candidate discovery

- walk the repository tree
- skip ignored directories like `.git`, `node_modules`, build output, virtual environments
- keep only text files with common source/code extensions
- cap file size to avoid scanning huge blobs

### Relevance scoring

- compute a relevance score per candidate using `LocalScorer` (fast term-overlap heuristic) by default
- optionally use `JevScorer` for live scoring via the Jev Decisions API (`--live` flag)
- any custom scorer can be plugged in via the `Scorer` protocol
- return a value between 0 and 1

### Confidence gate

- **accept** if score is above `accept_threshold` (default 0.65)
- **reject** if score is below `uncertain_threshold` (default 0.40)
- **uncertain** if score is between the two thresholds — escalate to fallback if configured
- optional `min_margin` check downgrades accept to uncertain when top scores are too close

### Fallback path

- optional function callback with signature like:

```python
callable[[str, str, str], float]
```

- receives: file path, query, content
- returns a float score or a boolean-like decision
- remains strictly optional

### Audit trail

Each search emits a compact trace like:

```json
[
  {"step": 1, "provider": "local", "score": 0.94, "decision": "accept", "path": "src/auth/middleware.py"},
  {"step": 2, "provider": "local", "score": 0.41, "decision": "uncertain", "path": "src/routes/api.py"},
  {"step": 3, "provider": "local", "score": 0.12, "decision": "reject", "path": "src/utils/math.py"}
]
```

## Quality bar

The tool should be considered good enough when it:

- works on a local directory without external setup
- returns likely files for a natural-language question
- remains deterministic in test mode
- does not require a large runtime or broad scaffolding
- produces a reasoned, inspectable result list

## Implementation constraints

- keep Python 3.11+ only
- keep dependencies minimal: standard library + a tiny CLI tool stack
- no hidden complexity or broad architecture assumptions
- maintain testability with local heuristics by default

## Proposed first release

Release 0.1.0 includes:

- basic repo scanning with configurable exclude lists
- dual scoring: LocalScorer (offline) and JevScorer (live via Jev API)
- three-way confidence gate with margin check
- optional fallback callback for uncertain candidates
- CLI with --live, --json, --verbose, --with-fallback, --min-margin
- security: state redactor, .env exclusion, secret-pattern filtering
- python-dotenv auto-loading
- 49 unit and integration tests

## Success metric

Success is defined as:

- the tool reliably finds likely relevant files for a repo question
- it remains cheap, explainable, and easy to test
- it does not grow beyond the narrow purpose of code search
