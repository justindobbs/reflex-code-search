#!/usr/bin/env python3
"""Benchmark harness for reflex-code-search.

Reads benchmarks/queries.json, runs each query through ReflexCodeSearcher
in local mode, and reports recall@k, latency, and summary statistics.

Usage:
    python tools/bench.py                          # local scorer only
    python tools/bench.py --live                   # also run with JevScorer
    python tools/bench.py --top-k 10               # override top_k
    python tools/bench.py --output results.md      # write markdown to file
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Resolve project root so imports work when run from any directory
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
load_dotenv(_PROJECT_ROOT / ".env")

from reflex_search.scorers import JevScorer, LocalScorer
from reflex_search.searcher import ReflexCodeSearcher


def _load_queries(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _normalise(p: str) -> str:
    """Normalise path separators for comparison."""
    return p.replace("\\", "/")


def _run_suite(
    suite: dict[str, Any],
    *,
    live: bool = False,
    top_k: int = 5,
    threshold: float = 0.30,
    max_queries: int | None = None,
) -> list[dict[str, Any]]:
    """Run all queries in a suite and return per-query results."""
    repo_root = str((_PROJECT_ROOT / suite["repo_root"]).resolve())
    results: list[dict[str, Any]] = []

    queries = suite["queries"][:max_queries] if max_queries else suite["queries"]
    total = len(queries)

    for idx, entry in enumerate(queries, 1):
        query = entry["query"]
        expected = {_normalise(p) for p in entry["expected_files"]}
        if live:
            print(f"    [{idx}/{total}] {query[:55]}...", end="", flush=True)

        scorer = JevScorer(timeout=15.0) if live else LocalScorer()
        searcher = ReflexCodeSearcher(
            repo_root=repo_root,
            scorer=scorer,
            accept_threshold=threshold,
            uncertain_threshold=0.10,
            top_k=top_k,
        )

        t0 = time.perf_counter()
        session = searcher.search(query)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

        returned = {_normalise(r.path) for r in session.results}
        hits = returned & expected
        recall = len(hits) / len(expected) if expected else 0.0

        total_cost = 0.0
        total_tokens = 0
        for step in session.audit_trail:
            total_cost += step.get("cost", 0.0)
            total_tokens += step.get("input_tokens", 0)

        result = {
            "query": query,
            "expected": sorted(expected),
            "returned": sorted(returned),
            "hits": sorted(hits),
            "missed": sorted(expected - returned),
            "recall": round(recall, 3),
            "latency_ms": elapsed_ms,
            "cost": round(total_cost, 6),
            "input_tokens": total_tokens,
            "provider": scorer.provider,
            "candidates_scored": len(session.audit_trail),
        }
        if live:
            print(f" {elapsed_ms:.0f}ms  {recall:.0%}")
        results.append(result)

    return results


def _format_markdown(
    all_results: dict[str, list[dict[str, Any]]],
    top_k: int,
    threshold: float,
) -> str:
    lines: list[str] = []
    lines.append("# Benchmark results\n")
    lines.append(f"**Settings:** top_k={top_k}, threshold={threshold}\n")

    for label, results in all_results.items():
        lines.append(f"## {label}\n")

        # Summary table
        lines.append("| Query | Recall | Latency (ms) | Cost | Tokens | Hits / Expected |")
        lines.append("|-------|--------|-------------|------|--------|-----------------|")

        total_recall = 0.0
        total_latency = 0.0
        total_cost = 0.0
        total_tokens = 0

        for r in results:
            total_recall += r["recall"]
            total_latency += r["latency_ms"]
            total_cost += r["cost"]
            total_tokens += r["input_tokens"]

            q_short = r["query"][:60] + ("..." if len(r["query"]) > 60 else "")
            lines.append(
                f"| {q_short} | {r['recall']:.0%} | {r['latency_ms']:.0f} | "
                f"${r['cost']:.4f} | {r['input_tokens']} | "
                f"{len(r['hits'])}/{len(r['expected'])} |"
            )

        n = len(results)
        avg_recall = total_recall / n if n else 0
        avg_latency = total_latency / n if n else 0
        lines.append(
            f"| **Average** | **{avg_recall:.0%}** | **{avg_latency:.0f}** | "
            f"**${total_cost:.4f}** | **{total_tokens}** | |"
        )
        lines.append("")

        # Missed files detail
        missed_any = [r for r in results if r["missed"]]
        if missed_any:
            lines.append("### Missed files\n")
            for r in missed_any:
                lines.append(f"- **{r['query'][:60]}**: {', '.join(r['missed'])}")
            lines.append("")

    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark reflex-code-search")
    parser.add_argument("--live", action="store_true", help="Also benchmark with JevScorer")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.30)
    parser.add_argument("--max-queries", type=int, default=None, help="Max queries per suite (useful for live)")
    parser.add_argument("--output", type=str, default=None, help="Write markdown to file")
    args = parser.parse_args()

    queries_path = _PROJECT_ROOT / "benchmarks" / "queries.json"
    if not queries_path.exists():
        print(f"ERROR: {queries_path} not found", file=sys.stderr)
        sys.exit(1)

    data = _load_queries(queries_path)
    all_results: dict[str, list[dict[str, Any]]] = {}

    for suite in data["suites"]:
        suite_root = (_PROJECT_ROOT / suite["repo_root"]).resolve()
        if not suite_root.exists():
            print(f"SKIP: {suite['name']} — repo not found at {suite_root}")
            continue

        label = f"{suite['name']} (local)"
        print(f"\n{'='*60}")
        print(f"Running: {label}")
        print(f"{'='*60}")

        results = _run_suite(suite, live=False, top_k=args.top_k, threshold=args.threshold, max_queries=args.max_queries)
        all_results[label] = results

        for r in results:
            status = "✓" if r["recall"] == 1.0 else f"✗ missed: {r['missed']}"
            print(f"  [{r['recall']:.0%}] {r['query'][:55]}  {status}")

        avg = sum(r["recall"] for r in results) / len(results) if results else 0
        print(f"\n  Average recall: {avg:.0%}  |  Avg latency: {sum(r['latency_ms'] for r in results)/len(results):.0f}ms")

        if args.live:
            label_live = f"{suite['name']} (jev)"
            print(f"\n{'='*60}")
            print(f"Running: {label_live}")
            print(f"{'='*60}")

            results_live = _run_suite(suite, live=True, top_k=args.top_k, threshold=args.threshold, max_queries=args.max_queries)
            all_results[label_live] = results_live

            for r in results_live:
                status = "✓" if r["recall"] == 1.0 else f"✗ missed: {r['missed']}"
                print(f"  [{r['recall']:.0%}] {r['query'][:55]}  {status}")

            avg = sum(r["recall"] for r in results_live) / len(results_live) if results_live else 0
            avg_lat = sum(r["latency_ms"] for r in results_live) / len(results_live) if results_live else 0
            total_cost = sum(r["cost"] for r in results_live)
            print(f"\n  Average recall: {avg:.0%}  |  Avg latency: {avg_lat:.0f}ms  |  Total cost: ${total_cost:.4f}")

    # Output
    md = _format_markdown(all_results, args.top_k, args.threshold)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md, encoding="utf-8")
        print(f"\nResults written to {out_path}")
    else:
        print(f"\n{'='*60}")
        print(md)


if __name__ == "__main__":
    main()
