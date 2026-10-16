# Contributing

Thanks for helping improve reflex-code-search. Keep changes focused on reliable,
explainable repository search and the project's offline-first design.

## Set up a development environment

Python 3.11 or newer is required.

```bash
python -m venv .venv

# Linux or macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
```

## Before opening a pull request

Run the checks used in CI:

```bash
python -m ruff check reflex_search/ tests/ tools/bench.py
python -m pytest tests/ -v
```

For changes to ranking, collection, or search behavior, run the local benchmark
and include relevant before-and-after results in the pull request:

```bash
python tools/bench.py
```

Live benchmarks call the Jev API and may incur cost. Use them only when the
change needs live scoring results and an API key is configured.

## Pull requests

- Explain the user-facing problem and the change that addresses it.
- Keep the implementation within the project's narrow code-search scope.
- Add or update documentation when behavior or CLI options change.
- Include tests for behavior changes and report which checks you ran.
- Avoid committing credentials, `.env` files, generated benchmark output, or
  unrelated formatting changes.

## Design constraints

- Keep local search usable without network access or API credentials.
- Keep runtime dependencies small.
- Preserve deterministic, inspectable behavior where practical.
- Do not add an IDE layer, symbolic code graph, multi-agent orchestration, or a
  broad plugin framework.
