# reflex-code-search architecture

This project is intentionally small. The goal is to create a lightweight, controllable code-search primitive that can be used by a coding agent or developer without dragging in a broad agent framework.

## Core idea

A natural-language code search should be modeled as a bounded decision problem:

- inspect likely files
- score relevance with a fast model
- accept high-confidence matches
- escalate uncertain cases to a stronger model
- stop once enough evidence is collected

That is the same basic pattern as the REFLEX control loop: bounded decisions first, fallback only when needed.

## Components

### 1. Candidate discovery

The searcher scans a repo and collects candidate text files, excluding common noise such as:

- `.git` directories
- build outputs
- virtual environments
- vendored dependencies
- large binary-like files

This step is meant to be cheap and deterministic.

### 2. Relevance scoring

Each file is scored against the user's query using a Jev-like relevance function. The implementation keeps a local heuristic by default so the project remains testable and works without a remote provider.

The scoring model is intentionally simple:

- overlap between query terms and file path
- overlap between query terms and file content
- limited preview size for efficient scanning

### 3. Confidence gate

The confidence gate decides whether a result is confident enough to accept or whether it should be skipped or escalated.

The design is intentionally conservative:

- high score → accept
- medium score → maybe fallback, if configured
- low score → skip

### 4. Fallback path

When a file is uncertain, the library may call a configured LLM fallback callback. This is optional and is kept separate from the core flow.

The fallback is not a substitute for the main flow. It is only there to resolve edge cases.

### 5. Audit trail

Every search emits a compact audit trail. This includes:

- step number
- provider used
- score
- path examined
- accept or skip decision

This keeps the tool explainable and makes debugging easier.

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
- a primitive that can be extended later without reworking the design

It is designed to be the opposite of mission creep: one narrow capability, done well.
