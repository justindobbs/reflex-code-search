# reflex-code-search

**Project site:** [reflex-code-search.netlify.app](https://reflex-code-search.netlify.app/)

[![CI](https://github.com/justindobbs/reflex-code-search/actions/workflows/ci.yml/badge.svg)](https://github.com/justindobbs/reflex-code-search/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A small, focused implementation of semantic code search using a REFLEX-style control loop:

- fast local relevance scoring with bigram matching and definition boosting (offline by default)
- optional live scoring via the [Jev Decisions API](https://openrouter.ai/api/alpha/decisions)
- three-way confidence gate (accept / uncertain / reject) with margin check
- optional fallback scorer for uncertain matches
- small, auditable search sessions with per-step telemetry
- repository discovery that respects nested `.gitignore` files
- CLI-first design for local repository discovery

This project is intentionally narrow. It is not a broad coding-agent runtime, IDE, or repo management platform. It is a minimal primitive: given a natural-language question, find the files most likely to be relevant.

## Project landing page

The static landing page is in [`site/index.html`](site/index.html). Preview the deployable site locally with:

```bash
python -m http.server 8000 --directory site
```

Then open `http://localhost:8000`. Netlify publishes this directory using [`netlify.toml`](netlify.toml); the page has no build step or JavaScript dependencies.

## Why this exists

Use a fast relevance model to narrow the search space before expensive reasoning. Many implementations end up becoming much larger and more complicated than the core need.

This project keeps the same idea while staying smaller and easier to reason about:

1. collect candidate files from a repo
2. score them with a fast local heuristic — or the Jev API via `--live`
3. gate each score: **accept**, **uncertain**, or **reject**
4. escalate uncertain cases to a fallback scorer when configured
5. return the best files plus a compact audit trail with telemetry

## Design goals

- keep the search loop small and explainable
- keep the control flow explicit: score → gate → fallback if uncertain
- keep outputs auditable, without hiding the decision path
- avoid mission creep into IDE workflows or orchestration layers

## Install

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -e .

# With dev tools (pytest, ruff)
pip install -e ".[dev]"
```

## Development checks

After installing the dev tools, run the test suite with pytest:

```bash
python -m pytest tests/ -v
```

Run Ruff to check code style and common issues:

```bash
python -m ruff check .
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor setup, checks, and pull
request guidance.

For vulnerability reporting and details about data sent during optional live
scoring, see [SECURITY.md](SECURITY.md).

## Usage

Display the CLI options and descriptions:

```bash
reflex-search --help
```

Basic search against the current directory:

```bash
reflex-search "How is scoring done?" .
```

```
[local] 0.84  reflex_search/scorers.py
  reason: Accepted by confidence gate
```

Lower the threshold to surface more candidates:

```bash
reflex-search "confidence gate" . --threshold 0.3
```

```
[local] 1.00  reflex_search/gate.py
[local] 0.76  docs/benchmarks.md
[local] 0.70  reflex_search/scorers.py
[local] 0.68  README.md
```

Verbose mode shows every candidate's score and the gate decision:

```bash
reflex-search "How is scoring done?" . --verbose --threshold 0.3
```

```
--- Audit Trail ---
  step   1  [local]  0.35  reject     CHANGELOG.md
  step   2  [local]  0.35  reject     docs/architecture.md
  step   3  [local]  0.26  reject     reflex_search/cli.py
  step   4  [local]  0.84  accept     reflex_search/scorers.py
  ...
```

JSON output for programmatic use:

```bash
reflex-search "confidence gate" . --json --threshold 0.3
```

With the built-in fallback scorer for uncertain candidates:

```bash
reflex-search "auth middleware" . --with-fallback --verbose
```

With smart Jev fallback — only uncertain candidates are sent to the API:

```bash
reflex-search "How is the audit trail structured?" . --smart-fallback --verbose
```

With live Jev API scoring (requires `OPENROUTER_API_KEY`):

```bash
reflex-search "How does the search loop work?" . --live --verbose
```

## CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--top-k` | 5 | Maximum number of files to return |
| `--threshold` | 0.65 | Accept threshold for the confidence gate |
| `--uncertain` | 0.40 | Uncertain threshold below which candidates are rejected |
| `--min-margin` | 0.0 | Minimum score margin required for an accept decision |
| `--with-fallback` | off | Enable the default fallback scorer |
| `--smart-fallback` | off | Use Jev API as fallback for uncertain candidates (mutually exclusive with `--with-fallback`) |
| `--live` | off | Two-pass: LocalScorer pre-filters, Jev re-scores shortlist |
| `--live-all` | off | Score every file with Jev (no pre-filter) |
| `--shortlist` | 20 | Number of files to shortlist for two-pass live mode |
| `--verbose` | off | Print the full audit trail after results |
| `--stats` | off | Print a one-line session telemetry summary |
| `--json` | off | Emit JSON instead of plain text (includes telemetry block) |

## Example output

```json
{
  "query": "How is authentication checked before requests reach the handler?",
  "repo_root": ".",
  "results": [
    {
      "path": "src/auth/middleware.py",
      "score": 0.85,
      "provider": "jev",
      "reason": "Accepted by confidence gate",
      "excerpt": "def require_auth(user):"
    }
  ],
  "audit_trail": [
    {
      "step": 1,
      "provider": "jev",
      "score": 0.85,
      "decision": "accept",
      "path": "src/auth/middleware.py",
      "latency_ms": 142.5,
      "cost": 0.0001,
      "input_tokens": 150
    }
  ]
}
```

## Library API

```python
from reflex_search import ReflexCodeSearcher

searcher = ReflexCodeSearcher(repo_root=".", accept_threshold=0.65)
session = searcher.search("Where are migrations defined?")

for result in session.results:
    print(result.path, result.score, result.provider)
```

With live Jev scoring:

```python
from reflex_search import JevScorer, ReflexCodeSearcher

searcher = ReflexCodeSearcher(scorer=JevScorer())
session = searcher.search("Where are migrations defined?")
```

A custom scorer can be plugged in via the `Scorer` protocol:

```python
from reflex_search.models import Scorer

class MyScorer:
    def score(self, file_path: str, query: str, content: str) -> float:
        ...

searcher = ReflexCodeSearcher(scorer=MyScorer())
```

## Jev API setup

To use `--live` or `JevScorer`, set your OpenRouter API key:

```bash
# Windows PowerShell
$env:OPENROUTER_API_KEY = "your-key"

# Linux / macOS
export OPENROUTER_API_KEY="your-key"
```

Without a key, `JevScorer` falls back to `LocalScorer` automatically.

## Relationship to tracecore-reflex

This project borrows design patterns from [tracecore-reflex](https://github.com/justindobbs/tracecore-reflex) — the confidence gate margin check, Jev API integration approach, and per-step telemetry — but does **not** depend on it at runtime. tracecore-reflex is an agent runtime for TraceCore tasks; this project is a narrow code-search primitive.

## Project structure

```text
reflex_search/
├── __init__.py        # public exports
├── __main__.py        # python -m reflex_search entrypoint
├── cli.py             # typer CLI
├── core.py            # backward-compatible re-exports
├── fallback.py        # default fallback scorer
├── file_collector.py  # repo file discovery and exclusions
├── gate.py            # three-way confidence gate
├── models.py          # data classes, Scorer protocol
├── scorers.py         # LocalScorer, JevScorer
└── searcher.py        # REFLEX search loop orchestrator

tests/
├── test_core.py       # unit tests for scorer, gate, searcher
└── test_cli.py        # CLI integration tests

benchmarks/
└── queries.json       # hand-labelled dataset (18 queries, 2 repos)

tools/
└── bench.py           # benchmark harness (recall@k, latency, cost)

docs/
├── architecture.md    # design and component docs
└── benchmarks.md      # benchmark results and jevgrep comparison
```

## License

MIT
