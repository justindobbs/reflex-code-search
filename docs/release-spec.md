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
  - provider (`jev` or `llm_fallback`)
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

- compute a relevance score per candidate using a fast local heuristic by default
- optional backend can later plug in a Jev-compatible model
- return a value between 0 and 1

### Confidence gate

- accept if score is above a threshold
- skip if clearly below threshold
- use the fallback path only if configured and score is borderline

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
  {"step": 1, "provider": "jev", "score": 0.94, "decision": "accept", "path": "src/auth/middleware.py"},
  {"step": 2, "provider": "jev", "score": 0.61, "decision": "skip", "path": "src/routes/api.py"}
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

Release 0.1.0 should include:

- basic repo scanning
- file relevance scoring
- threshold-based selection
- optional fallback callback
- CLI and JSON output
- unit tests covering core scenarios

## Success metric

Success is defined as:

- the tool reliably finds likely relevant files for a repo question
- it remains cheap, explainable, and easy to test
- it does not grow beyond the narrow purpose of code search
