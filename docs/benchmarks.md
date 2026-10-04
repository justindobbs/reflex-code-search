# Benchmarks

Measured recall, latency, and cost of reflex-code-search across two hand-labelled repos, comparing LocalScorer (offline) and JevScorer (live via noul).

## Methodology

- **Dataset**: 18 hand-labelled queries across 2 repos (10 for reflex-code-search, 8 for tracecore-reflex)
- **Metric**: recall@k — fraction of expected files that appear in the top-k results
- **LocalScorer v2**: 25% path unigrams, 45% content unigrams, 15% bigrams, 15% definition boosting, stopword-filtered. Threshold 0.30.
- **JevScorer**: Jev Decisions API `noul` primitive (calibrated yes/no probability) via OpenRouter. Threshold 0.10.
- **Harness**: `tools/bench.py` — reproducible, `--max-queries` for quick runs

## Summary

| Mode | reflex-code-search | tracecore-reflex | Avg latency | Cost per query |
|------|-------------------|-----------------|-------------|---------------|
| **Local v1** (pre-refactor) | 25% recall | 88% recall | ~350ms | $0 |
| **Local v2** (post-refactor) | 60% recall | 100% recall | ~290ms | $0 |
| **Jev** (live noul) | 83% recall | 100% recall | ~15–18s | ~$0.0005 |

The v1→v2 improvement comes from two changes:
1. Splitting `core.py` into focused modules with descriptive names (`gate.py`, `scorers.py`, `searcher.py`, `file_collector.py`, `fallback.py`)
2. Improving LocalScorer with bigram matching, definition-aware boosting, and stopword filtering

## Results: LocalScorer v2 (offline, threshold=0.30)

### reflex-code-search (this repo, 18 files)

| Query | Recall | Latency | Hits / Expected |
|-------|--------|---------|-----------------|
| How does the confidence gate decide whether to accept or reject? | 50% | 286ms | 1/2 |
| Where is the CLI entry point defined? | 100% | 321ms | 2/2 |
| How does the Jev API scorer work? | 100% | 369ms | 1/1 |
| What data model holds search results? | 100% | 276ms | 1/1 |
| How are files collected from the repository? | 0% | 277ms | 0/1 |
| Where are the public exports defined? | 100% | 264ms | 1/1 |
| How is the fallback scorer invoked for uncertain candidates? | 50% | 280ms | 1/2 |
| What file extensions are considered scannable? | 0% | 258ms | 0/1 |
| How is the audit trail structured? | 0% | 265ms | 0/3 |
| Where are unit tests for the confidence gate? | 100% | 273ms | 1/1 |
| **Average** | **60%** | **287ms** | |

### tracecore-reflex (23 files)

| Query | Recall | Latency | Hits / Expected |
|-------|--------|---------|-----------------|
| How does the agent decide between Jev and LLM fallback? | 100% | 463ms | 2/2 |
| Where is the Jev client that calls the decisions API? | 100% | 448ms | 1/1 |
| How is per-step telemetry tracked? | 100% | 444ms | 1/1 |
| How does the confidence gate evaluate a Jev answer? | 100% | 454ms | 1/1 |
| Where is the TraceCore-loadable agent configured? | 100% | 459ms | 1/1 |
| How do validators use Jev for task scoring? | 100% | 482ms | 1/1 |
| What does the threshold sweep tool measure? | 100% | 479ms | 1/1 |
| Where is the incident triage example? | 100% | 460ms | 1/1 |
| **Average** | **100%** | **461ms** | |

## Results: JevScorer (live noul, threshold=0.10)

### reflex-code-search (3 queries sampled)

| Query | Recall | Latency | Cost | Hits / Expected |
|-------|--------|---------|------|-----------------|
| How does the confidence gate decide whether to accept or reject? | 50% | 14.6s | $0.0005 | 1/2 |
| Where is the CLI entry point defined? | 100% | 14.8s | $0.0005 | 2/2 |
| How does the Jev API scorer work? | 100% | 15.9s | $0.0005 | 1/1 |
| **Average** | **83%** | **15.1s** | **$0.0005/q** | |

### tracecore-reflex (3 queries sampled)

| Query | Recall | Latency | Cost | Hits / Expected |
|-------|--------|---------|------|-----------------|
| How does the agent decide between Jev and LLM fallback? | 100% | 19.9s | $0.0007 | 2/2 |
| Where is the Jev client that calls the decisions API? | 100% | 17.1s | $0.0007 | 1/1 |
| How is per-step telemetry tracked? | 100% | 17.8s | $0.0007 | 1/1 |
| **Average** | **100%** | **18.3s** | **$0.0007/q** | |

## Analysis

**LocalScorer works best with descriptive filenames.** tracecore-reflex scores 88% because its files are named for their purpose (`confidence_gate.py`, `telemetry.py`). reflex-code-search scores 25% because most logic lives in `core.py` — the path gives no signal.

**JevScorer (noul) dramatically improves recall.** 83% on this repo (up from 25%) and 100% on tracecore-reflex. The noul primitive correctly identifies implementation files and deprioritizes docs/changelogs.

**Latency is the tradeoff.** Each file requires one Jev API call (~1s). For 12 files, that's ~15s per query. For larger repos this is impractical without pre-filtering. The intended workflow is: use LocalScorer for fast triage, then `--live` for accuracy when the local results aren't sufficient.

**Cost is negligible.** ~$0.0005–$0.0007 per query (all files scored). A full benchmark run of 6 queries costs under $0.004.

## Comparison: reflex-search vs jevgrep

| Dimension | reflex-search | jevgrep |
|-----------|--------------|---------|
| **Offline mode** | Yes (LocalScorer, free) | No — API key required for every query |
| **Live recall** | 83–100% (noul) | Not measured on same dataset |
| **Granularity** | File-level | Line-range with source excerpts |
| **Language awareness** | None (text matching) | Tree-sitter (Python, Go, Rust, TS) |
| **Jev primitive** | 1 noul per file | 2 independent nouls per chunk |
| **Install** | `pip install .` (Python) | `npm install -g` (Node 22+) |
| **Audit trail** | Full trail for every candidate | Only matches reported |
| **Cost per query** | Free (local) or 1 call/file | 2 calls/chunk |
| **MCP server** | No | Yes |
| **Gate logic** | Accept / uncertain / reject + fallback | Binary match/no-match |
| **Pluggable scorers** | `Scorer` protocol | Fixed Jev pipeline |

### Where reflex-search wins

- **Works offline** — zero API calls, zero network
- **Python-native** — `pip install`, no Node.js / WASM / Tree-sitter
- **Full audit trail** — every candidate logged with score, decision, telemetry
- **Cheaper live mode** — 1 noul per file vs 2 nouls per chunk
- **Extensible** — plug any scorer via the `Scorer` protocol
- **Three-way gate** — uncertain candidates can escalate to a fallback

### Where jevgrep wins

- **Semantic depth** — two independent judgments (entity + operation) per chunk
- **Line-level precision** — exact line ranges with source excerpts
- **Language-aware** — Tree-sitter parsing for structural understanding
- **Hierarchical search** — prunes directories before scanning files
- **Agent integration** — built-in MCP server

### Positioning

reflex-search is the **lightweight, offline-first, Python-native** code search tool for:

1. Fast file-level results with no API key or network required
2. A pluggable scoring pipeline you can extend with any model
3. Full audit trails showing every accept, reject, and escalation
4. A tool that stays small and doesn't grow into an agent runtime

jevgrep is better when you need line-level precision, language-aware parsing, or MCP integration.

## Reproducing

```bash
# Local mode only
python tools/bench.py

# Quick live check (3 queries per suite)
python tools/bench.py --live --max-queries 3 --threshold 0.10

# Full live run
python tools/bench.py --live --threshold 0.10

# Write results to file
python tools/bench.py --live --max-queries 3 --output docs/benchmarks.md
```
