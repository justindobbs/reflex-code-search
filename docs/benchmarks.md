# Benchmark results

**Settings:** top_k=5, threshold=0.3

Recall@k, precision@k, and reciprocal rank are macro-averaged across queries; precision@k uses the requested k as its denominator.

The independent Click suite uses upstream tag 8.5.0 and expects its checkout at `.benchmark-repos/click`; CI checks it out automatically.

## reflex-code-search (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does the confidence gate decide whether to accept or rej... | 50% | 20% | 0.50 | 68 | $0.0000 | 0 | 1/2 |
| Where is the CLI entry point defined? | 50% | 20% | 1.00 | 49 | $0.0000 | 0 | 1/2 |
| How does the Jev API scorer work? | 100% | 20% | 0.20 | 48 | $0.0000 | 0 | 1/1 |
| What data model holds search results? | 100% | 20% | 0.25 | 52 | $0.0000 | 0 | 1/1 |
| How are files collected from the repository? | 100% | 20% | 1.00 | 63 | $0.0000 | 0 | 1/1 |
| Where are the public exports defined? | 100% | 20% | 0.20 | 60 | $0.0000 | 0 | 1/1 |
| How is the fallback scorer invoked for uncertain candidates? | 50% | 20% | 0.33 | 54 | $0.0000 | 0 | 1/2 |
| What file extensions are considered scannable? | 100% | 20% | 0.25 | 103 | $0.0000 | 0 | 1/1 |
| How is the audit trail structured? | 33% | 20% | 0.25 | 173 | $0.0000 | 0 | 1/3 |
| Where are unit tests for the confidence gate? | 100% | 20% | 1.00 | 70 | $0.0000 | 0 | 1/1 |
| How does the local scorer handle synonym expansion? | 100% | 20% | 0.33 | 46 | $0.0000 | 0 | 1/1 |
| Where is docstring boosting implemented? | 100% | 20% | 0.50 | 52 | $0.0000 | 0 | 1/1 |
| How does the two-pass live search reduce API calls? | 50% | 20% | 0.25 | 48 | $0.0000 | 0 | 1/2 |
| What aggregate telemetry is available after a search session... | 50% | 20% | 0.33 | 49 | $0.0000 | 0 | 1/2 |
| How does the smart Jev fallback differ from the default fall... | 100% | 20% | 0.33 | 45 | $0.0000 | 0 | 1/1 |
| Where is the benchmark harness that runs recall tests? | 100% | 40% | 1.00 | 56 | $0.0000 | 0 | 2/2 |
| What dependencies does the project require? | 100% | 20% | 0.33 | 48 | $0.0000 | 0 | 1/1 |
| How does the stemmer normalize query terms? | 100% | 20% | 0.33 | 46 | $0.0000 | 0 | 1/1 |
| Where are the gitignore exclusion rules applied during file ... | 50% | 20% | 1.00 | 53 | $0.0000 | 0 | 1/2 |
| How is the project architecture documented? | 100% | 20% | 0.33 | 43 | $0.0000 | 0 | 1/1 |
| How does Jev scoring protect secrets before sending file con... | 100% | 40% | 0.50 | 49 | $0.0000 | 0 | 2/2 |
| How does JevScorer fall back locally after an API error? | 100% | 20% | 1.00 | 49 | $0.0000 | 0 | 1/1 |
| How does the file collector use nested .gitignore patterns? | 100% | 40% | 0.33 | 53 | $0.0000 | 0 | 2/2 |
| Where are session telemetry fields defined and calculated? | 50% | 20% | 0.25 | 55 | $0.0000 | 0 | 1/2 |
| Where does the command line turn search results into JSON? | 100% | 20% | 1.00 | 56 | $0.0000 | 0 | 1/1 |
| What text suffixes are allowed and what file size is too lar... | 100% | 20% | 0.33 | 51 | $0.0000 | 0 | 1/1 |
| When does the search loop escalate an uncertain score to its... | 100% | 20% | 0.20 | 46 | $0.0000 | 0 | 1/1 |
| How does the local ranking score Python module docstrings? | 100% | 40% | 1.00 | 49 | $0.0000 | 0 | 2/2 |
| **Average** | **85%** | **23%** | **0.51** | **58** | **$0.0000** | **0** | |

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
| How does the agent decide between Jev and LLM fallback? | 100% | 40% | 1.00 | 136 | $0.0000 | 0 | 2/2 |
| Where is the Jev client that calls the decisions API? | 100% | 20% | 1.00 | 53 | $0.0000 | 0 | 1/1 |
| How is per-step telemetry tracked? | 100% | 20% | 1.00 | 43 | $0.0000 | 0 | 1/1 |
| How does the confidence gate evaluate a Jev answer? | 100% | 20% | 1.00 | 45 | $0.0000 | 0 | 1/1 |
| Where is the TraceCore-loadable agent configured? | 100% | 20% | 1.00 | 62 | $0.0000 | 0 | 1/1 |
| How do validators use Jev for task scoring? | 100% | 20% | 1.00 | 45 | $0.0000 | 0 | 1/1 |
| What does the threshold sweep tool measure? | 100% | 20% | 1.00 | 42 | $0.0000 | 0 | 1/1 |
| Where is the incident triage example? | 100% | 20% | 1.00 | 50 | $0.0000 | 0 | 1/1 |
| How are action arguments resolved from a Jev response? | 100% | 40% | 1.00 | 44 | $0.0000 | 0 | 2/2 |
| How does the natural escalation example demonstrate the REFL... | 100% | 20% | 1.00 | 43 | $0.0000 | 0 | 1/1 |
| Where does the policy comparison example compare different a... | 100% | 20% | 0.33 | 53 | $0.0000 | 0 | 1/1 |
| How does the run report tool summarize experiment results? | 100% | 20% | 0.50 | 45 | $0.0000 | 0 | 1/1 |
| What does the compare_runs tool do? | 100% | 40% | 1.00 | 44 | $0.0000 | 0 | 2/2 |
| How are step-level labels assigned and tested? | 100% | 40% | 1.00 | 51 | $0.0000 | 0 | 2/2 |
| Where is the project configuration for model names and gate ... | 0% | 0% | 0.00 | 57 | $0.0000 | 0 | 0/2 |
| What experiment checklist guides reproducible runs? | 100% | 20% | 1.00 | 65 | $0.0000 | 0 | 1/1 |
| **Average** | **94%** | **24%** | **0.86** | **55** | **$0.0000** | **0** | |

### Missed files

- **Where is the project configuration for model names and gate **: pyproject.toml, reflex.toml

## click (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does Click parse command line arguments and option value... | 100% | 40% | 0.33 | 241 | $0.0000 | 0 | 2/2 |
| Where are Group and resolve_command implemented? | 100% | 20% | 0.20 | 248 | $0.0000 | 0 | 1/1 |
| Where are the command, group, and option decorators defined? | 100% | 20% | 1.00 | 219 | $0.0000 | 0 | 1/1 |
| Where is Click's HelpFormatter implemented and used? | 100% | 40% | 1.00 | 258 | $0.0000 | 0 | 2/2 |
| How can tests run a command and capture its output without a... | 100% | 20% | 0.50 | 188 | $0.0000 | 0 | 1/1 |
| How are Click's Path and File parameter types defined? | 100% | 20% | 0.20 | 233 | $0.0000 | 0 | 1/1 |
| How does Click generate shell-specific command completions? | 100% | 20% | 1.00 | 171 | $0.0000 | 0 | 1/1 |
| Where are command usage errors represented and shown? | 100% | 40% | 1.00 | 232 | $0.0000 | 0 | 2/2 |
| **Average** | **100%** | **28%** | **0.65** | **224** | **$0.0000** | **0** | |
