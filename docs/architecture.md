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

### 1. Candidate discovery (`file_collector.collect_files`)

The searcher scans a repo and collects candidate text files, excluding common noise such as:

- `.git` directories
- build outputs
- virtual environments
- vendored dependencies
- large binary-like files (>250 KB)

It also respects `.gitignore` files at the repository root and in nested directories,
including negated patterns that re-include files. The built-in exclusions above still
apply even if an ignore rule would otherwise re-include a path.

This step is meant to be cheap and deterministic.

### 2. Relevance scoring

The `Scorer` protocol (defined in `models.py`) allows plugging in any scorer. Two implementations are provided:

#### `LocalScorer` (default, offline)

A fast term-overlap heuristic with no API calls. It expands a bounded synonym
map and combines path matches (25%), content matches in the first 8,000
characters (35%), phrase matches (15%), definition-name matches (15%), and
Python docstring matches (10%). Each component is normalized by query term
count; original terms weigh more than expanded synonyms. Phrase matching
normalizes hyphens and underscores, and treats “fall back” as “fallback.”
Location and implementation queries also get a direct symbol-match boost of up
to 20%, before the final score is capped at 1.0.

#### `JevScorer` (live, requires API key)

Calls the [Jev Decisions API](https://openrouter.ai/api/alpha/decisions) via OpenRouter using the **noul** primitive — a calibrated yes/no probability that judges whether a file contains the implementation answering the query. Documentation and changelogs that merely mention a topic are deprioritized. The API is called directly with `httpx`; there is no runtime dependency on an agent framework or another code-search package.

On API errors, HTTP 401 (bad key), or HTTP 429 (rate limited), `JevScorer` falls back to `LocalScorer` automatically with a log warning. Each call records `latency_ms`, `cost`, and `input_tokens` for the audit trail. A `state_redactor` callback strips lines matching common secret patterns before content is sent to the API.

### 3. Confidence gate (`ConfidenceGate`)

The confidence gate makes a **three-way decision** for each candidate:

| Score range | Decision | Action |
|-------------|----------|--------|
| ≥ `accept_threshold` (default 0.65) | **accept** | Add to results |
| ≥ `uncertain_threshold` (default 0.40) | **uncertain** | Escalate to fallback if configured; otherwise return as a candidate lead |
| < `uncertain_threshold` | **reject** | Return a positive-scoring candidate lead separately from accepted results |

Candidate leads are exposed in `SearchSession.candidates` and the CLI/MCP
`candidates` field. They include the gate decision and supporting excerpt, but
are never mixed into `results`. Zero-score files are omitted from this list.

When `min_margin` is enabled, the searcher compares the highest candidate score
with the runner-up. A close top result is downgraded to **uncertain**. The gate
also rejects NaN, infinity, and non-numeric scores; finite scores outside [0, 1]
are clamped.

### 4. Fallback path (`default_fallback_scorer`, `JevFallback`)

When a candidate is **uncertain**, the searcher calls an optional fallback scorer. The fallback result is run through the same confidence gate.

The built-in `default_fallback_scorer` uses simple term overlap. `JevFallback`
uses the Jev API and records call telemetry. They are enabled with
`--with-fallback` and `--smart-fallback`, respectively, or by passing a callable
to `ReflexCodeSearcher(fallback=...)`.

The fallback is not a substitute for the main flow. It is only there to resolve edge cases.

### 5. Audit trail and telemetry

Every search emits a compact audit trail. This includes:

- step number
- provider used (`local`, `jev`, or `fallback`)
- score
- path examined
- decision (`accept`, `uncertain`, or `reject`)

When using `JevScorer` or `JevFallback`, entries also include:

- `latency_ms` — round-trip time for the API call
- `cost` — token cost from the Jev response
- `input_tokens` — number of input tokens consumed

This keeps the tool explainable and makes debugging easier. The `--verbose` CLI flag prints the full audit trail. Two-pass search records first-pass `prefilter` entries and second-pass Jev decisions; session decision counts exclude prefilter events, and `files_scanned` counts unique candidate paths.

When fallback runs, the audit trail records both the original uncertain decision
and the fallback decision, including telemetry for each scorer call.

## Relationship to tracecore-reflex

This project borrows design patterns from [tracecore-reflex](https://github.com/justindobbs/tracecore-reflex):

- the Jev API call structure and endpoint
- the margin-based confidence gate
- per-step telemetry fields (latency, cost, tokens)

It does **not** import or depend on tracecore-reflex at runtime. tracecore-reflex is an agent runtime for multi-step TraceCore tasks; this project is a single-shot file ranker. The useful ideas were ported directly to keep the projects decoupled.

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
