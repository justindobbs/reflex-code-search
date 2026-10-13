# Benchmark results

**Settings:** top_k=5, threshold=0.3

## reflex-code-search (local)

| Query | Recall | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|--------|-------------|------|--------|-----------------|
| How does the confidence gate decide whether to accept or rej... | 50% | 78 | $0.0000 | 0 | 1/2 |
| Where is the CLI entry point defined? | 50% | 22 | $0.0000 | 0 | 1/2 |
| How does the Jev API scorer work? | 100% | 25 | $0.0000 | 0 | 1/1 |
| What data model holds search results? | 100% | 29 | $0.0000 | 0 | 1/1 |
| How are files collected from the repository? | 100% | 21 | $0.0000 | 0 | 1/1 |
| Where are the public exports defined? | 100% | 21 | $0.0000 | 0 | 1/1 |
| How is the fallback scorer invoked for uncertain candidates? | 50% | 29 | $0.0000 | 0 | 1/2 |
| What file extensions are considered scannable? | 100% | 24 | $0.0000 | 0 | 1/1 |
| How is the audit trail structured? | 33% | 41 | $0.0000 | 0 | 1/3 |
| Where are unit tests for the confidence gate? | 100% | 33 | $0.0000 | 0 | 1/1 |
| How does the local scorer handle synonym expansion? | 100% | 24 | $0.0000 | 0 | 1/1 |
| Where is docstring boosting implemented? | 100% | 23 | $0.0000 | 0 | 1/1 |
| How does the two-pass live search reduce API calls? | 50% | 27 | $0.0000 | 0 | 1/2 |
| What aggregate telemetry is available after a search session... | 50% | 24 | $0.0000 | 0 | 1/2 |
| How does the smart Jev fallback differ from the default fall... | 100% | 22 | $0.0000 | 0 | 1/1 |
| Where is the benchmark harness that runs recall tests? | 100% | 22 | $0.0000 | 0 | 2/2 |
| What dependencies does the project require? | 100% | 20 | $0.0000 | 0 | 1/1 |
| How does the stemmer normalize query terms? | 100% | 26 | $0.0000 | 0 | 1/1 |
| Where are the gitignore exclusion rules applied during file ... | 100% | 39 | $0.0000 | 0 | 2/2 |
| How is the project architecture documented? | 100% | 34 | $0.0000 | 0 | 2/2 |
| **Average** | **84%** | **29** | **$0.0000** | **0** | |

### Missed files

- **How does the confidence gate decide whether to accept or rej**: reflex_search/models.py
- **Where is the CLI entry point defined?**: reflex_search/__main__.py
- **How is the fallback scorer invoked for uncertain candidates?**: reflex_search/searcher.py
- **How is the audit trail structured?**: reflex_search/models.py, reflex_search/searcher.py
- **How does the two-pass live search reduce API calls?**: reflex_search/cli.py
- **What aggregate telemetry is available after a search session**: reflex_search/searcher.py

## tracecore-reflex (local)

| Query | Recall | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|--------|-------------|------|--------|-----------------|
| How does the agent decide between Jev and LLM fallback? | 100% | 671 | $0.0000 | 0 | 2/2 |
| Where is the Jev client that calls the decisions API? | 100% | 88 | $0.0000 | 0 | 1/1 |
| How is per-step telemetry tracked? | 100% | 89 | $0.0000 | 0 | 1/1 |
| How does the confidence gate evaluate a Jev answer? | 100% | 113 | $0.0000 | 0 | 1/1 |
| Where is the TraceCore-loadable agent configured? | 100% | 98 | $0.0000 | 0 | 1/1 |
| How do validators use Jev for task scoring? | 100% | 96 | $0.0000 | 0 | 1/1 |
| What does the threshold sweep tool measure? | 100% | 75 | $0.0000 | 0 | 1/1 |
| Where is the incident triage example? | 100% | 61 | $0.0000 | 0 | 1/1 |
| How are action arguments resolved from a Jev response? | 100% | 56 | $0.0000 | 0 | 2/2 |
| How does the natural escalation example demonstrate the REFL... | 100% | 52 | $0.0000 | 0 | 1/1 |
| Where does the policy comparison example compare different a... | 100% | 52 | $0.0000 | 0 | 1/1 |
| How does the run report tool summarize experiment results? | 100% | 52 | $0.0000 | 0 | 1/1 |
| What does the compare_runs tool do? | 100% | 48 | $0.0000 | 0 | 2/2 |
| How are step-level labels assigned and tested? | 100% | 46 | $0.0000 | 0 | 2/2 |
| Where is the project configuration for model names and gate ... | 0% | 57 | $0.0000 | 0 | 0/2 |
| What experiment checklist guides reproducible runs? | 100% | 49 | $0.0000 | 0 | 1/1 |
| **Average** | **94%** | **106** | **$0.0000** | **0** | |

### Missed files

- **Where is the project configuration for model names and gate **: pyproject.toml, reflex.toml
