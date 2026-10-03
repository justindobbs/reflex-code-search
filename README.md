# reflex-code-search

A clean, focused implementation of semantic code search using a REFLEX-style control loop:

- Jev-like relevance checks for fast, bounded file ranking
- Optional LLM fallback for uncertain cases
- Small, auditable search sessions with step-by-step reasoning
- Minimal CLI for local repository discovery

This project is intentionally narrow. It is not a broad coding-agent runtime, IDE, or repository management platform. It is a small, useful primitive: given a natural-language question, find the most likely files to inspect.

## Why this exists

The original Jevgrep idea is strong: use a fast relevance model to narrow the search space before expensive reasoning. But more elaborate repos often add large amounts of infrastructure, extra search modes, and broad agent behavior that can obscure the core value.

This project keeps the same idea while making the control flow simpler and more explicit:

1. gather text candidates from a repo
2. score them with a bounded relevance check
3. escalate uncertain cases to an LLM fallback when configured
4. return the best files with a compact audit trail

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Usage

```bash
reflex-search "How is authentication checked before requests reach the handler?" .
```

With JSON output:

```bash
reflex-search "Where are migrations defined?" . --json
```

## Example output

```json
{
  "query": "How is authentication checked before requests reach the handler?",
  "results": [
    {
      "path": "src/auth/middleware.py",
      "score": 0.95,
      "provider": "jev",
      "reason": "Strong overlap between query terms and auth enforcement logic"
    }
  ],
  "audit_trail": [
    {
      "step": 1,
      "provider": "jev",
      "score": 0.95,
      "decision": "accept"
    }
  ]
}
```

## Design goals

- Keep the core search loop small and explainable
- Use Jev-like checks only when they help reduce search cost
- Keep full search traces for debugging and compliance
- Keep the CLI and library easy to test
- Avoid mission creep into IDE features or broad agent orchestration

## Project structure

```text
reflex_search/
├── __init__.py
├── core.py
├── cli.py
└── models.py

tests/
└── test_searcher.py
```

## License

MIT
