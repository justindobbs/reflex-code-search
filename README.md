# reflex-code-search

**Project site:** [reflex-code-search.netlify.app](https://reflex-code-search.netlify.app/)

[![CI](https://github.com/justindobbs/reflex-code-search/actions/workflows/ci.yml/badge.svg)](https://github.com/justindobbs/reflex-code-search/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A small, focused implementation of semantic code search using a REFLEX-style control loop:

- fast local relevance scoring with bigram matching and definition boosting (offline by default)
- optional live scoring via the [Jev Decisions API](https://openrouter.ai/docs/guides/community/jev)
- three-way confidence gate (accept / uncertain / reject) with margin check
- optional fallback scorer for uncertain matches
- small, auditable search sessions with per-step telemetry
- repository discovery that respects nested `.gitignore` files
- CLI-first design for local repository discovery

This project is intentionally narrow. It is not a broad coding-agent runtime, IDE, or repo management platform. It is a minimal primitive: given a natural-language question, find the files most likely to be relevant.

## Why this exists

Coding agents and developer tools regularly need to answer "which files matter for this question?" before they can do anything useful. The common approaches each have a gap:

- **Grep and ripgrep** find exact tokens but miss semantic intent — a query about "how authentication works" won't match a file that calls its function `verify_session`.
- **Embedding-based search** requires an index, a vector store, and ongoing sync with the repo. That's a lot of infrastructure for a question that should take milliseconds.
- **Sending the whole repo to a large model** works until the repo is too big, too expensive, or too slow — and it's hard to audit which files the model actually considered.

reflex-code-search sits in the gap: use a fast relevance model to narrow the search space before expensive reasoning, without the infrastructure overhead. The approach stays small and easy to reason about:

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

## Benchmarks

The benchmark harness scores queries against this repo, `tracecore-reflex` (expected at `../tracecore-reflex`), and two third-party repos. The third-party checkouts live in `.benchmark-repos/` which is gitignored, so clone them before running benchmarks locally:

```bash
git clone --depth 1 --branch 8.5.0 https://github.com/pallets/click.git .benchmark-repos/click
git clone --depth 1 --branch 0.28.1 https://github.com/encode/httpx.git .benchmark-repos/httpx
```

Then run the harness:

```bash
python tools/bench.py
```

CI checks out both repos automatically. Results are in [docs/benchmarks.md](docs/benchmarks.md).

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
| `--async` | off | Use async parallel scoring for `--live` and `--smart-fallback` modes |

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

Async parallel scoring (smart-fallback with concurrency limit):

```python
import asyncio
from reflex_search import AsyncJevScorer, ReflexCodeSearcher

searcher = ReflexCodeSearcher(repo_root=".", accept_threshold=0.30, uncertain_threshold=0.10)
session = asyncio.run(
    searcher.async_search("Where are migrations defined?", concurrency=10)
)
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

## Agent integration

### Agent Skills (zero dependencies)

The `skills/code-search/SKILL.md` file tells any compatible agent (Windsurf, Claude Code, etc.) how to invoke reflex-search via the CLI. No SDK or server process needed — agents read the skill file and run the CLI directly.

### MCP server (optional dependency)

For agents that speak the [Model Context Protocol](https://modelcontextprotocol.io/), reflex-code-search exposes a `search_codebase` tool:

```bash
# Install with MCP support
pip install -e ".[mcp]"

# Run the MCP server (stdio transport)
reflex-search-mcp
# or
python -m reflex_search.mcp_server
```

The tool accepts `query`, `repo_root`, `top_k`, `threshold`, `live`, and `smart_fallback` parameters and returns structured JSON matching the `SearchSession` shape.

## Project structure

```text
reflex_search/
├── __init__.py        # public exports
├── __main__.py        # python -m reflex_search entrypoint
├── ast_extract.py     # AST-based Python metadata extraction
├── cli.py             # typer CLI
├── core.py            # backward-compatible re-exports
├── fallback.py        # default fallback scorer
├── file_collector.py  # repo file discovery and exclusions
├── gate.py            # three-way confidence gate
├── mcp_server.py      # MCP tool server (optional mcp dependency)
├── models.py          # data classes, Scorer protocol
├── scorers.py         # LocalScorer, JevScorer, AsyncJevScorer
└── searcher.py        # REFLEX search loop orchestrator (sync + async)

skills/
└── code-search/
    └── SKILL.md       # Agent Skills definition for CLI invocation

tests/
├── test_ast_extract.py # AST extractor tests
├── test_async.py      # async scorer and search tests
├── test_cli.py        # CLI integration tests
├── test_core.py       # unit tests for scorer, gate, searcher
├── test_file_collector.py # file collector tests
└── test_mcp.py        # MCP server tests

benchmarks/
└── queries.json       # hand-labelled dataset (4 repos, 60 queries)

tools/
├── bench.py           # benchmark harness (recall@k, latency, cost)
└── precision_analysis.py # false-accept analysis tool

docs/
├── architecture.md    # design and component docs
└── benchmarks.md      # benchmark results
```

## License

MIT
