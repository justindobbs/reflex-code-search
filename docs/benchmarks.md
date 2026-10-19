# Benchmark results

**Settings:** top_k=5, threshold=0.3

Recall@k, precision@k, and reciprocal rank are macro-averaged across queries; precision@k uses the requested k as its denominator.

The independent Click suite uses upstream tag 8.5.0 and expects its checkout at `.benchmark-repos/click`; CI checks it out automatically.

## reflex-code-search (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does the confidence gate decide whether to accept or rej... | 100% | 40% | 0.50 | 2041 | $0.0000 | 0 | 2/2 |
| Where is the CLI entry point defined? | 100% | 40% | 1.00 | 180 | $0.0000 | 0 | 2/2 |
| How does the Jev API scorer work? | 100% | 20% | 1.00 | 140 | $0.0000 | 0 | 1/1 |
| What data model holds search results? | 100% | 20% | 0.50 | 128 | $0.0000 | 0 | 1/1 |
| How are files collected from the repository? | 100% | 20% | 1.00 | 141 | $0.0000 | 0 | 1/1 |
| Where are the public exports defined? | 100% | 20% | 0.33 | 139 | $0.0000 | 0 | 1/1 |
| How is the fallback scorer invoked for uncertain candidates? | 100% | 40% | 1.00 | 129 | $0.0000 | 0 | 2/2 |
| What file extensions are considered scannable? | 100% | 20% | 0.50 | 178 | $0.0000 | 0 | 1/1 |
| How is the audit trail structured? | 100% | 60% | 1.00 | 194 | $0.0000 | 0 | 3/3 |
| Where are unit tests for the confidence gate? | 100% | 20% | 1.00 | 130 | $0.0000 | 0 | 1/1 |
| How does the local scorer handle synonym expansion? | 100% | 20% | 1.00 | 212 | $0.0000 | 0 | 1/1 |
| Where is docstring boosting implemented? | 100% | 20% | 0.50 | 210 | $0.0000 | 0 | 1/1 |
| How does the two-pass live search reduce API calls? | 100% | 40% | 0.33 | 131 | $0.0000 | 0 | 2/2 |
| What aggregate telemetry is available after a search session... | 100% | 40% | 1.00 | 184 | $0.0000 | 0 | 2/2 |
| How does the smart Jev fallback differ from the default fall... | 100% | 20% | 1.00 | 156 | $0.0000 | 0 | 1/1 |
| Where is the benchmark harness that runs recall tests? | 100% | 40% | 0.50 | 159 | $0.0000 | 0 | 2/2 |
| What dependencies does the project require? | 100% | 20% | 1.00 | 151 | $0.0000 | 0 | 1/1 |
| How does the stemmer normalize query terms? | 100% | 20% | 1.00 | 153 | $0.0000 | 0 | 1/1 |
| Where are the gitignore exclusion rules applied during file ... | 100% | 40% | 0.50 | 141 | $0.0000 | 0 | 2/2 |
| How is the project architecture documented? | 100% | 20% | 1.00 | 130 | $0.0000 | 0 | 1/1 |
| How does Jev scoring protect secrets before sending file con... | 100% | 40% | 1.00 | 137 | $0.0000 | 0 | 2/2 |
| How does JevScorer fall back locally after an API error? | 100% | 20% | 1.00 | 130 | $0.0000 | 0 | 1/1 |
| How does the file collector use nested .gitignore patterns? | 100% | 40% | 1.00 | 125 | $0.0000 | 0 | 2/2 |
| Where are session telemetry fields defined and calculated? | 100% | 40% | 1.00 | 144 | $0.0000 | 0 | 2/2 |
| Where does the command line turn search results into JSON? | 100% | 20% | 0.50 | 149 | $0.0000 | 0 | 1/1 |
| What text suffixes are allowed and what file size is too lar... | 100% | 20% | 1.00 | 131 | $0.0000 | 0 | 1/1 |
| When does the search loop escalate an uncertain score to its... | 100% | 20% | 0.33 | 132 | $0.0000 | 0 | 1/1 |
| How does the local ranking score Python module docstrings? | 100% | 40% | 1.00 | 131 | $0.0000 | 0 | 2/2 |
| **Average** | **100%** | **29%** | **0.80** | **218** | **$0.0000** | **0** | |

## tracecore-reflex (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does the agent decide between Jev and LLM fallback? | 100% | 40% | 1.00 | 124 | $0.0000 | 0 | 2/2 |
| Where is the Jev client that calls the decisions API? | 100% | 20% | 1.00 | 96 | $0.0000 | 0 | 1/1 |
| How is per-step telemetry tracked? | 100% | 20% | 1.00 | 94 | $0.0000 | 0 | 1/1 |
| How does the confidence gate evaluate a Jev answer? | 100% | 20% | 1.00 | 161 | $0.0000 | 0 | 1/1 |
| Where is the TraceCore-loadable agent configured? | 100% | 20% | 1.00 | 122 | $0.0000 | 0 | 1/1 |
| How do validators use Jev for task scoring? | 100% | 20% | 1.00 | 96 | $0.0000 | 0 | 1/1 |
| What does the threshold sweep tool measure? | 100% | 20% | 1.00 | 90 | $0.0000 | 0 | 1/1 |
| Where is the incident triage example? | 100% | 20% | 1.00 | 98 | $0.0000 | 0 | 1/1 |
| How are action arguments resolved from a Jev response? | 100% | 20% | 1.00 | 90 | $0.0000 | 0 | 1/1 |
| How does the natural escalation example demonstrate the REFL... | 100% | 20% | 1.00 | 95 | $0.0000 | 0 | 1/1 |
| Where does the policy comparison example compare different a... | 100% | 20% | 0.33 | 112 | $0.0000 | 0 | 1/1 |
| How does the run report tool summarize experiment results? | 100% | 20% | 0.50 | 95 | $0.0000 | 0 | 1/1 |
| What does the compare_runs tool do? | 100% | 40% | 1.00 | 95 | $0.0000 | 0 | 2/2 |
| How are step-level labels assigned and tested? | 100% | 40% | 1.00 | 80 | $0.0000 | 0 | 2/2 |
| Where are jev_model, fallback_model, threshold, and min_marg... | 100% | 20% | 1.00 | 150 | $0.0000 | 0 | 1/1 |
| What experiment checklist guides reproducible runs? | 100% | 20% | 1.00 | 80 | $0.0000 | 0 | 1/1 |
| **Average** | **100%** | **24%** | **0.93** | **105** | **$0.0000** | **0** | |

## click (local)

| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |
|-------|----------|------------|-----|-------------|------|--------|-----------------|
| How does Click parse command line arguments and option value... | 100% | 40% | 0.50 | 312 | $0.0000 | 0 | 2/2 |
| Where are Group and resolve_command implemented? | 100% | 20% | 0.20 | 293 | $0.0000 | 0 | 1/1 |
| Where are the command, group, and option decorators defined? | 100% | 20% | 1.00 | 259 | $0.0000 | 0 | 1/1 |
| Where is Click's HelpFormatter implemented and used? | 100% | 40% | 1.00 | 281 | $0.0000 | 0 | 2/2 |
| How can tests run a command and capture its output without a... | 100% | 20% | 0.50 | 232 | $0.0000 | 0 | 1/1 |
| How are Click's Path and File parameter types defined? | 100% | 20% | 0.50 | 288 | $0.0000 | 0 | 1/1 |
| How does Click generate shell-specific command completions? | 100% | 20% | 1.00 | 238 | $0.0000 | 0 | 1/1 |
| Where are command usage errors represented and shown? | 100% | 40% | 1.00 | 279 | $0.0000 | 0 | 2/2 |
| **Average** | **100%** | **28%** | **0.71** | **273** | **$0.0000** | **0** | |
