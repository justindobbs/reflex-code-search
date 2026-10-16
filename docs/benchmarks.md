# Benchmark results

**Settings:** top_k=5, threshold=0.3

Recall@k, precision@k, and reciprocal rank are macro-averaged across queries; precision@k uses the requested k as its denominator.

## reflex-code-search (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does the confidence gate decide whether to accept or rej... | 50% | 20% | 0.50 | 41 | $0.0000 | 0 | 1/2 |
| Where is the CLI entry point defined? | 50% | 20% | 0.33 | 36 | $0.0000 | 0 | 1/2 |
| How does the Jev API scorer work? | 100% | 20% | 0.20 | 38 | $0.0000 | 0 | 1/1 |
| What data model holds search results? | 100% | 20% | 0.25 | 23 | $0.0000 | 0 | 1/1 |
| How are files collected from the repository? | 100% | 20% | 1.00 | 25 | $0.0000 | 0 | 1/1 |
| Where are the public exports defined? | 100% | 20% | 0.20 | 24 | $0.0000 | 0 | 1/1 |
| How is the fallback scorer invoked for uncertain candidates? | 50% | 20% | 0.33 | 29 | $0.0000 | 0 | 1/2 |
| What file extensions are considered scannable? | 100% | 20% | 0.20 | 32 | $0.0000 | 0 | 1/1 |
| How is the audit trail structured? | 33% | 20% | 0.25 | 27 | $0.0000 | 0 | 1/3 |
| Where are unit tests for the confidence gate? | 100% | 20% | 1.00 | 26 | $0.0000 | 0 | 1/1 |
| How does the local scorer handle synonym expansion? | 100% | 20% | 0.33 | 26 | $0.0000 | 0 | 1/1 |
| Where is docstring boosting implemented? | 100% | 20% | 1.00 | 25 | $0.0000 | 0 | 1/1 |
| How does the two-pass live search reduce API calls? | 50% | 20% | 0.25 | 28 | $0.0000 | 0 | 1/2 |
| What aggregate telemetry is available after a search session... | 50% | 20% | 0.33 | 28 | $0.0000 | 0 | 1/2 |
| How does the smart Jev fallback differ from the default fall... | 100% | 20% | 0.33 | 25 | $0.0000 | 0 | 1/1 |
| Where is the benchmark harness that runs recall tests? | 100% | 40% | 1.00 | 24 | $0.0000 | 0 | 2/2 |
| What dependencies does the project require? | 100% | 20% | 0.33 | 26 | $0.0000 | 0 | 1/1 |
| How does the stemmer normalize query terms? | 100% | 20% | 0.33 | 24 | $0.0000 | 0 | 1/1 |
| Where are the gitignore exclusion rules applied during file ... | 50% | 20% | 0.50 | 27 | $0.0000 | 0 | 1/2 |
| How is the project architecture documented? | 100% | 40% | 0.33 | 26 | $0.0000 | 0 | 2/2 |
| How does Jev scoring protect secrets before sending file con... | 100% | 40% | 0.50 | 26 | $0.0000 | 0 | 2/2 |
| How does JevScorer fall back locally after an API error? | 100% | 20% | 0.33 | 28 | $0.0000 | 0 | 1/1 |
| How does the file collector use nested .gitignore patterns? | 100% | 40% | 0.33 | 26 | $0.0000 | 0 | 2/2 |
| Where are session telemetry fields defined and calculated? | 50% | 20% | 0.20 | 24 | $0.0000 | 0 | 1/2 |
| Where does the command line turn search results into JSON? | 100% | 20% | 0.25 | 27 | $0.0000 | 0 | 1/1 |
| What text suffixes are allowed and what file size is too lar... | 100% | 20% | 0.50 | 32 | $0.0000 | 0 | 1/1 |
| When does the search loop escalate an uncertain score to its... | 100% | 20% | 0.20 | 25 | $0.0000 | 0 | 1/1 |
| How does the local ranking score Python module docstrings? | 100% | 40% | 1.00 | 25 | $0.0000 | 0 | 2/2 |
| **Average** | **85%** | **24%** | **0.44** | **28** | **$0.0000** | **0** | |

### Missed files

- **How does the confidence gate decide whether to accept or rej**: reflex_search/models.py
- **Where is the CLI entry point defined?**: reflex_search/__main__.py
- **How is the fallback scorer invoked for uncertain candidates?**: reflex_search/searcher.py
- **How is the audit trail structured?**: reflex_search/models.py, reflex_search/searcher.py
- **How does the two-pass live search reduce API calls?**: reflex_search/cli.py
- **What aggregate telemetry is available after a search session**: reflex_search/searcher.py
- **Where are the gitignore exclusion rules applied during file **: reflex_search/file_collector.py
- **Where are session telemetry fields defined and calculated?**: reflex_search/searcher.py

## tracecore-reflex (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does the agent decide between Jev and LLM fallback? | 100% | 40% | 1.00 | 76 | $0.0000 | 0 | 2/2 |
| Where is the Jev client that calls the decisions API? | 100% | 20% | 0.50 | 70 | $0.0000 | 0 | 1/1 |
| How is per-step telemetry tracked? | 100% | 20% | 1.00 | 54 | $0.0000 | 0 | 1/1 |
| How does the confidence gate evaluate a Jev answer? | 100% | 20% | 1.00 | 59 | $0.0000 | 0 | 1/1 |
| Where is the TraceCore-loadable agent configured? | 100% | 20% | 1.00 | 62 | $0.0000 | 0 | 1/1 |
| How do validators use Jev for task scoring? | 100% | 20% | 1.00 | 61 | $0.0000 | 0 | 1/1 |
| What does the threshold sweep tool measure? | 100% | 20% | 1.00 | 68 | $0.0000 | 0 | 1/1 |
| Where is the incident triage example? | 100% | 20% | 1.00 | 70 | $0.0000 | 0 | 1/1 |
| How are action arguments resolved from a Jev response? | 100% | 40% | 1.00 | 53 | $0.0000 | 0 | 2/2 |
| How does the natural escalation example demonstrate the REFL... | 100% | 20% | 1.00 | 51 | $0.0000 | 0 | 1/1 |
| Where does the policy comparison example compare different a... | 100% | 20% | 0.50 | 57 | $0.0000 | 0 | 1/1 |
| How does the run report tool summarize experiment results? | 100% | 20% | 0.50 | 59 | $0.0000 | 0 | 1/1 |
| What does the compare_runs tool do? | 100% | 40% | 1.00 | 58 | $0.0000 | 0 | 2/2 |
| How are step-level labels assigned and tested? | 100% | 40% | 1.00 | 56 | $0.0000 | 0 | 2/2 |
| Where is the project configuration for model names and gate ... | 0% | 0% | 0.00 | 80 | $0.0000 | 0 | 0/2 |
| What experiment checklist guides reproducible runs? | 100% | 20% | 1.00 | 60 | $0.0000 | 0 | 1/1 |
| **Average** | **94%** | **24%** | **0.84** | **62** | **$0.0000** | **0** | |

### Missed files

- **Where is the project configuration for model names and gate **: pyproject.toml, reflex.toml
