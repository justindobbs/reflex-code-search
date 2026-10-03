# reflex-code-search architecture

This project is intentionally small. The goal is to create a lightweight, controllable code-search primitive that can be used by a coding agent or developer without dragging in a broad agent framework.

## Core idea

A natural-language code search should be modeled as a bounded decision problem:

- inspect likely files
- score relevance with a fast model
- **accept** high-confidence matches
- **escalate** uncertain cases to a fallback scorer
- **reject** low-confidence matches
- stop once enough evidence is collected

That is the same basic pattern as the REFLEX control loop: bounded decisions first, fallback only when needed.

## Components

### 1. Candidate discovery (`ReflexCodeSearcher._collect_files`)

The searcher scans a repo and collects candidate text files, excluding common noise such as:

- `.git` directories
- build outputs
- virtual environments
- vendored dependencies
- large binary-like files (>250 KB)

This step is meant to be cheap and deterministic.

### 2. Relevance scoring

The `Scorer` protocol (defined in `models.py`) allows plugging in any scorer. Two implementations are provided:

#### `LocalScorer` (default, offline)

A fast term-overlap heuristic with no API calls:

- 30% weight: overlap between query terms and file path
- 70% weight: overlap between query terms and file content (first 2000 chars)
- both components normalized by the number of query terms

#### `JevScorer` (live, requires API key)

Calls the [Jev Decisions API](https://openrouter.ai/api/alpha/decisions) via OpenRouter using the **score** primitive with a five-level relevance rubric. This is the same API used by [tracecore-reflex](https://github.com/justindobbs/tracecore-reflex), but called directly with `httpx` — no dependency on the tracecore-reflex package.

On API errors or missing keys, `JevScorer` falls back to `LocalScorer` automatically. Each call records `latency_ms`, `cost`, and `input_tokens` for the audit trail.

### 3. Confidence gate (`ConfidenceGate`)

The confidence gate makes a **three-way decision** for each candidate:

| Score range | Decision | Action |
|-------------|----------|--------|
| ≥ `accept_threshold` (default 0.65) | **accept** | Add to results |
| ≥ `uncertain_threshold` (default 0.40) | **uncertain** | Escalate to fallback if configured, otherwise skip |
| < `uncertain_threshold` | **reject** | Skip immediately |

The gate also includes two hardening features ported from tracecore-reflex:

- **`min_margin`** — if the gap between the candidate's score and a runner-up is below this margin, the decision is downgraded from accept to uncertain (prevents false confidence in ambiguous results)
- **Input validation** — NaN, infinity, non-numeric, and out-of-range scores are rejected gracefully

### 4. Fallback path (`default_fallback_scorer`)

When a candidate is **uncertain**, the searcher calls an optional fallback scorer. The fallback result is run through the same confidence gate.

The built-in `default_fallback_scorer` uses simple term overlap. It is enabled via the `--with-fallback` CLI flag or by passing a callable to `ReflexCodeSearcher(fallback=...)`.

The fallback is not a substitute for the main flow. It is only there to resolve edge cases.

### 5. Audit trail and telemetry

Every search emits a compact audit trail. This includes:

- step number
- provider used (`local`, `jev`, or `fallback`)
- score
- path examined
- decision (`accept`, `uncertain`, or `reject`)

When using `JevScorer`, each entry also includes:

- `latency_ms` — round-trip time for the API call
- `cost` — token cost from the Jev response
- `input_tokens` — number of input tokens consumed

This keeps the tool explainable and makes debugging easier. The `--verbose` CLI flag prints the full audit trail.

## Relationship to tracecore-reflex

This project borrows proven design patterns from tracecore-reflex:

- the Jev API call structure and endpoint
- the margin-based confidence gate
- per-step telemetry fields (latency, cost, tokens)

It does **not** import or depend on tracecore-reflex at runtime. tracecore-reflex is an agent runtime for multi-step TraceCore tasks; this project is a single-shot file ranker. The useful ideas were ported directly (~60 lines of new code) to keep the projects decoupled.

## Why this stays small

The project intentionally avoids a large number of features:

- no symbolic code graph
- no repository-wide summarization engine
- no multi-agent orchestration
- no broad plugin system
- no IDE integration layer

Those may be useful later, but they are not required to solve the core problem cleanly.

## Intended usage

This is meant to be used as:

- a library inside agent workflows
- a small CLI for local repo search
- a primitive that can be extended later via the `Scorer` protocol

It is designed to be the opposite of mission creep: one narrow capability, done well.
