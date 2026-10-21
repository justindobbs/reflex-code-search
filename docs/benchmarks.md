# Benchmark results

**Settings:** top_k=5, threshold=0.3

Recall@k, precision@k, and reciprocal rank are macro-averaged across queries; precision@k uses the requested k as its denominator.

The independent Click suite uses upstream tag 8.5.0 and expects its checkout at `.benchmark-repos/click`; the httpx suite uses upstream tag 0.28.1 at `.benchmark-repos/httpx`. CI checks out both automatically.

## reflex-code-search (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does the confidence gate decide whether to accept or rej... | 100% | 40% | 1.00 | 72 | $0.0000 | 0 | 2/2 |
| Where is the CLI entry point defined? | 100% | 40% | 1.00 | 47 | $0.0000 | 0 | 2/2 |
| How does the Jev API scorer work? | 100% | 20% | 1.00 | 47 | $0.0000 | 0 | 1/1 |
| What data model holds search results? | 100% | 20% | 0.50 | 51 | $0.0000 | 0 | 1/1 |
| How are files collected from the repository? | 100% | 20% | 1.00 | 45 | $0.0000 | 0 | 1/1 |
| Where are the public exports defined? | 100% | 20% | 0.50 | 52 | $0.0000 | 0 | 1/1 |
| How is the fallback scorer invoked for uncertain candidates? | 100% | 40% | 1.00 | 43 | $0.0000 | 0 | 2/2 |
| What file extensions are considered scannable? | 100% | 20% | 0.50 | 36 | $0.0000 | 0 | 1/1 |
| How is the audit trail structured? | 100% | 60% | 1.00 | 44 | $0.0000 | 0 | 3/3 |
| Where are unit tests for the confidence gate? | 100% | 20% | 1.00 | 48 | $0.0000 | 0 | 1/1 |
| How does the local scorer handle synonym expansion? | 100% | 20% | 1.00 | 44 | $0.0000 | 0 | 1/1 |
| Where is docstring boosting implemented? | 100% | 20% | 1.00 | 41 | $0.0000 | 0 | 1/1 |
| How does the two-pass live search reduce API calls? | 100% | 40% | 0.50 | 39 | $0.0000 | 0 | 2/2 |
| What aggregate telemetry is available after a search session... | 100% | 40% | 1.00 | 51 | $0.0000 | 0 | 2/2 |
| How does the smart Jev fallback differ from the default fall... | 100% | 20% | 1.00 | 38 | $0.0000 | 0 | 1/1 |
| Where is the benchmark harness that runs recall tests? | 100% | 40% | 0.50 | 42 | $0.0000 | 0 | 2/2 |
| What dependencies does the project require? | 100% | 20% | 1.00 | 45 | $0.0000 | 0 | 1/1 |
| How does the stemmer normalize query terms? | 100% | 20% | 1.00 | 38 | $0.0000 | 0 | 1/1 |
| Where are the gitignore exclusion rules applied during file ... | 100% | 40% | 0.50 | 41 | $0.0000 | 0 | 2/2 |
| How is the project architecture documented? | 100% | 20% | 1.00 | 35 | $0.0000 | 0 | 1/1 |
| How does Jev scoring protect secrets before sending file con... | 50% | 20% | 1.00 | 35 | $0.0000 | 0 | 1/2 |
| How does JevScorer fall back locally after an API error? | 100% | 20% | 1.00 | 41 | $0.0000 | 0 | 1/1 |
| How does the file collector use nested .gitignore patterns? | 100% | 40% | 1.00 | 39 | $0.0000 | 0 | 2/2 |
| Where are session telemetry fields defined and calculated? | 100% | 40% | 1.00 | 69 | $0.0000 | 0 | 2/2 |
| Where does the command line turn search results into JSON? | 100% | 20% | 0.50 | 49 | $0.0000 | 0 | 1/1 |
| What text suffixes are allowed and what file size is too lar... | 100% | 20% | 1.00 | 40 | $0.0000 | 0 | 1/1 |
| When does the search loop escalate an uncertain score to its... | 100% | 20% | 0.50 | 41 | $0.0000 | 0 | 1/1 |
| How does the local ranking score Python module docstrings? | 100% | 40% | 1.00 | 36 | $0.0000 | 0 | 2/2 |
| **Average** | **98%** | **29%** | **0.86** | **45** | **$0.0000** | **0** | |

### Missed files

- **How does Jev scoring protect secrets before sending file con**: tests/test_core.py

## tracecore-reflex (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does the agent decide between Jev and LLM fallback? | 100% | 40% | 1.00 | 308 | $0.0000 | 0 | 2/2 |
| Where is the Jev client that calls the decisions API? | 100% | 20% | 1.00 | 118 | $0.0000 | 0 | 1/1 |
| How is per-step telemetry tracked? | 100% | 20% | 1.00 | 79 | $0.0000 | 0 | 1/1 |
| How does the confidence gate evaluate a Jev answer? | 100% | 20% | 1.00 | 90 | $0.0000 | 0 | 1/1 |
| Where is the TraceCore-loadable agent configured? | 100% | 20% | 1.00 | 102 | $0.0000 | 0 | 1/1 |
| How do validators use Jev for task scoring? | 100% | 20% | 1.00 | 78 | $0.0000 | 0 | 1/1 |
| What does the threshold sweep tool measure? | 100% | 20% | 1.00 | 73 | $0.0000 | 0 | 1/1 |
| Where is the incident triage example? | 100% | 20% | 1.00 | 97 | $0.0000 | 0 | 1/1 |
| How are action arguments resolved from a Jev response? | 100% | 20% | 1.00 | 73 | $0.0000 | 0 | 1/1 |
| How does the natural escalation example demonstrate the REFL... | 100% | 20% | 1.00 | 70 | $0.0000 | 0 | 1/1 |
| Where does the policy comparison example compare different a... | 100% | 20% | 0.50 | 78 | $0.0000 | 0 | 1/1 |
| How does the run report tool summarize experiment results? | 100% | 20% | 0.50 | 73 | $0.0000 | 0 | 1/1 |
| What does the compare_runs tool do? | 100% | 40% | 1.00 | 75 | $0.0000 | 0 | 2/2 |
| How are step-level labels assigned and tested? | 100% | 40% | 1.00 | 71 | $0.0000 | 0 | 2/2 |
| Where are jev_model, fallback_model, threshold, and min_marg... | 100% | 20% | 1.00 | 108 | $0.0000 | 0 | 1/1 |
| What experiment checklist guides reproducible runs? | 100% | 20% | 1.00 | 67 | $0.0000 | 0 | 1/1 |
| **Average** | **100%** | **24%** | **0.94** | **98** | **$0.0000** | **0** | |

## click (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does Click parse command line arguments and option value... | 100% | 40% | 0.50 | 240 | $0.0000 | 0 | 2/2 |
| Where are Group and resolve_command implemented? | 100% | 20% | 1.00 | 203 | $0.0000 | 0 | 1/1 |
| Where are the command, group, and option decorators defined? | 100% | 20% | 1.00 | 193 | $0.0000 | 0 | 1/1 |
| Where is Click's HelpFormatter implemented and used? | 100% | 40% | 1.00 | 245 | $0.0000 | 0 | 2/2 |
| How can tests run a command and capture its output without a... | 100% | 20% | 1.00 | 222 | $0.0000 | 0 | 1/1 |
| How are Click's Path and File parameter types defined? | 100% | 20% | 1.00 | 298 | $0.0000 | 0 | 1/1 |
| How does Click generate shell-specific command completions? | 100% | 20% | 1.00 | 303 | $0.0000 | 0 | 1/1 |
| Where are command usage errors represented and shown? | 100% | 40% | 1.00 | 369 | $0.0000 | 0 | 2/2 |
| **Average** | **100%** | **28%** | **0.94** | **259** | **$0.0000** | **0** | |

## httpx (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does httpx follow redirects? | 100% | 20% | 0.50 | 723 | $0.0000 | 0 | 1/1 |
| Where are the Request and Response classes defined? | 100% | 20% | 0.50 | 203 | $0.0000 | 0 | 1/1 |
| How does authentication work in httpx? | 100% | 20% | 0.33 | 154 | $0.0000 | 0 | 1/1 |
| Where is the async HTTP client implemented? | 100% | 20% | 1.00 | 183 | $0.0000 | 0 | 1/1 |
| How does httpx handle streaming responses? | 0% | 0% | 0.00 | 734 | $0.0000 | 0 | 0/2 |
| Where is URL parsing and manipulation implemented? | 100% | 40% | 1.00 | 277 | $0.0000 | 0 | 2/2 |
| How does the transport layer send requests? | 100% | 40% | 1.00 | 209 | $0.0000 | 0 | 2/2 |
| Where is the exception hierarchy defined? | 100% | 20% | 1.00 | 205 | $0.0000 | 0 | 1/1 |
| **Average** | **88%** | **22%** | **0.67** | **336** | **$0.0000** | **0** | |

### Missed files

- **How does httpx handle streaming responses?**: httpx/_client.py, httpx/_models.py

## httpx — Local vs Smart-Fallback comparison

Smart-fallback uses LocalScorer for initial ranking and escalates uncertain candidates
(score between 0.10 and 0.30) to Jev via the decisions API.  Run with
`python tools/bench.py --smart-fallback --suite httpx`.

| Metric | Local | Smart-Fallback | Delta |
|--------|-------|----------------|-------|
| Recall@5 | 81% | 88% | **+7 pp** |
| MRR | 0.58 | 0.65 | +0.07 |
| Precision@5 | 20% | 22% | +2 pp |
| Avg latency | 157 ms | 49,290 ms | +49 s |
| Total cost (8 queries) | $0.00 | $0.0115 | +$0.01 |
| Total Jev fallback calls | 0 | 339 | — |
| Avg fallback calls / query | 0 | 42 | — |

### What improved

- **"How does httpx handle streaming responses?"** — local missed both expected files
  (`_client.py`, `_models.py`). Smart-fallback recovered `_models.py` (recall 0% → 50%).

### What stayed the same

- **"How does the transport layer send requests?"** — still misses
  `httpx/_transports/default.py` in both modes. Jev scored it above the accept
  threshold in isolated tests, but 42+ uncertain candidates per query dilute the
  top-5 slots.

### Takeaways

1. Smart-fallback closes some conceptual gaps that LocalScorer cannot bridge.
2. The current uncertain band (0.10–0.30) triggers ~42 Jev calls per query on httpx,
   making wall-clock time impractical for routine use. Narrowing the band or batching
   calls (Phase 4: async scoring) would reduce this.
3. Cost per query is low (~$0.0014) but latency dominates at ~1 s per Jev call
   sequentially.

## Precision improvements (Phase 2)

File-type demotions reduce noise from test, doc, tool, and example files when
queries ask about implementation.  The demotions are guarded by intent checks
so queries explicitly about those categories are unaffected.

| Category | FAs before | FAs after | Demotion factor |
|----------|-----------|----------|-----------------|
| test     | 50        | 31       | 0.65            |
| doc      | 43        | 8        | 0.55            |
| tool     | 13        | 10       | 0.60            |
| example  | (in other)| 6        | 0.50            |
| other    | 81        | 110      | —               |
| **total**| **188**   | **160**  | —               |

The remaining "other" FAs are sibling source files (e.g. `_api.py`, `core.py`)
that share vocabulary with the expected file.  These require semantic
understanding (Phase 3) or Jev fallback to resolve.
