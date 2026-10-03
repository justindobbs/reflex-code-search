# reflex-code-search

A small, focused implementation of semantic code search using a REFLEX-style control loop:

- fast bounded relevance scoring for file ranking
- optional LLM fallback for uncertain matches
- small, auditable search sessions with step-by-step reasoning
- CLI-first design for local repository discovery

This project is intentionally narrow. It is not a broad coding-agent runtime, IDE, or repo management platform. It is a minimal primitive: given a natural-language question, find the files most likely to be relevant.

## Why this exists

The core idea behind Jevgrep is valuable: use a fast relevance model to narrow the search space before expensive reasoning. But many implementations end up becoming much larger and more complicated than the core need.

This project keeps the same idea while staying smaller and easier to reason about:

1. collect candidate files from a repo
2. score them with a bounded relevance check
3. escalate uncertain cases to an LLM fallback when configured
4. return the best files plus a compact audit trail

## Design goals

- keep the search loop small and explainable
- keep the control flow explicit: score, gate, fallback if necessary
- keep outputs auditable, without hiding the decision path
- avoid mission creep into IDE workflows or orchestration layers

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
  "repo_root": ".",
  "results": [
    {
      "path": "src/auth/middleware.py",
      "score": 0.95,
      "provider": "jev",
      "reason": "Strong relevance score for auth enforcement logic"
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

## Project structure

```text
reflex_search/
├── __init__.py
├── __main__.py
├── cli.py
├── core.py
└── models.py

tests/
└── test_searcher.py
```

## License

MIT
