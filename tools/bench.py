
"""Benchmark harness for reflex-code-search.

Reads benchmarks/queries.json, runs each query through ReflexCodeSearcher
in local mode, and reports recall@k, latency, and summary statistics.

Usage:
    python tools/bench.py                          # local scorer only
    python tools/bench.py --smart-fallback          # local + Jev fallback for uncertain
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

from reflex_search.fallback import JevFallback
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
    smart_fallback: bool = False,
    top_k: int = 5,
    threshold: float = 0.30,
    max_queries: int | None = None,
) -> list[dict[str, Any]]:
    """Run all queries in a suite and return per-query results."""
    repo_root = str((_PROJECT_ROOT / suite["repo_root"]).resolve())
    results: list[dict[str, Any]] = []

    queries = suite["queries"][:max_queries] if max_queries else suite["queries"]
    total = len(queries)
    show_progress = live or smart_fallback

    for idx, entry in enumerate(queries, 1):
        query = entry["query"]
        expected = {_normalise(p) for p in entry["expected_files"]}
        if show_progress:
            print(f"    [{idx}/{total}] {query[:55]}...", end="", flush=True)

        scorer = JevScorer(timeout=15.0) if live else LocalScorer()
        fallback = JevFallback(timeout=15.0) if smart_fallback else None
        searcher = ReflexCodeSearcher(
            repo_root=repo_root,
            scorer=scorer,
            fallback=fallback,
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
        ranked_returned = [_normalise(r.path) for r in session.results]
        first_relevant_rank = next(
            (rank for rank, path in enumerate(ranked_returned, start=1) if path in expected),
            None,
        )
        precision = len(hits) / top_k if top_k else 0.0

        total_cost = 0.0
        total_tokens = 0
        for step in session.audit_trail:
            total_cost += step.get("cost", 0.0)
            total_tokens += step.get("input_tokens", 0)

        fallback_calls = sum(
            1 for step in session.audit_trail
            if step.get("provider") in ("jev-fallback",)
        )

        result = {
            "query": query,
            "expected": sorted(expected),
            "returned": sorted(returned),
            "hits": sorted(hits),
            "missed": sorted(expected - returned),
            "recall": round(recall, 3),
            "precision_at_k": round(precision, 3),
            "reciprocal_rank": round(1 / first_relevant_rank, 3) if first_relevant_rank else 0.0,
            "latency_ms": elapsed_ms,
            "cost": round(total_cost, 6),
            "input_tokens": total_tokens,
            "provider": scorer.provider,
            "candidates_scored": len(session.audit_trail),
            "fallback_calls": fallback_calls,
        }
        if show_progress:
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
    lines.append(
        "Recall@k, precision@k, and reciprocal rank are macro-averaged across "
        "queries; precision@k uses the requested k as its denominator.\n"
    )
    lines.append(
        "The independent Click suite uses upstream tag 8.5.0 and expects its "
        "checkout at `.benchmark-repos/click`; the httpx suite uses upstream tag "
        "0.28.1 at `.benchmark-repos/httpx`. CI checks out both automatically.\n"
    )

    for label, results in all_results.items():
        lines.append(f"## {label}\n")

        # Summary table
        lines.append("| Query | Recall@k | Precision@k | MRR | Latency (ms) | Cost | Tokens | Hits / Expected |")
        lines.append("|-------|----------|------------|-----|-------------|------|--------|-----------------|")

        total_recall = 0.0
        total_latency = 0.0
        total_cost = 0.0
        total_tokens = 0
        total_precision = 0.0
        total_reciprocal_rank = 0.0

        for r in results:
            total_recall += r["recall"]
            total_latency += r["latency_ms"]
            total_cost += r["cost"]
            total_tokens += r["input_tokens"]
            total_precision += r["precision_at_k"]
            total_reciprocal_rank += r["reciprocal_rank"]

            q_short = r["query"][:60] + ("..." if len(r["query"]) > 60 else "")
            lines.append(
                f"| {q_short} | {r['recall']:.0%} | {r['precision_at_k']:.0%} | "
                f"{r['reciprocal_rank']:.2f} | {r['latency_ms']:.0f} | "
                f"${r['cost']:.4f} | {r['input_tokens']} | "
                f"{len(r['hits'])}/{len(r['expected'])} |"
            )

        n = len(results)
        avg_recall = total_recall / n if n else 0
        avg_precision = total_precision / n if n else 0
        avg_reciprocal_rank = total_reciprocal_rank / n if n else 0
        avg_latency = total_latency / n if n else 0
        lines.append(
            f"| **Average** | **{avg_recall:.0%}** | **{avg_precision:.0%}** | "
            f"**{avg_reciprocal_rank:.2f}** | **{avg_latency:.0f}** | "
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
    parser.add_argument("--smart-fallback", action="store_true", help="Also benchmark with Local + Jev fallback")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.30)
    parser.add_argument("--suite", type=str, default=None, help="Run only the named suite (e.g. httpx)")
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
        if args.suite and suite["name"] != args.suite:
            continue
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
            status = "[ok]" if r["recall"] == 1.0 else f"[missed: {r['missed']}]"
            print(f"  [{r['recall']:.0%}] {r['query'][:55]}  {status}")

        avg = sum(r["recall"] for r in results) / len(results) if results else 0
        print(f"\n  Average recall: {avg:.0%}  |  Avg latency: {sum(r['latency_ms'] for r in results)/len(results):.0f}ms")

        if args.smart_fallback:
            label_sf = f"{suite['name']} (smart-fallback)"
            print(f"\n{'='*60}")
            print(f"Running: {label_sf}")
            print(f"{'='*60}")

            results_sf = _run_suite(suite, smart_fallback=True, top_k=args.top_k, threshold=args.threshold, max_queries=args.max_queries)
            all_results[label_sf] = results_sf

            for r in results_sf:
                status = "[ok]" if r["recall"] == 1.0 else f"[missed: {r['missed']}]"
                fb = f"  fb={r['fallback_calls']}" if r["fallback_calls"] else ""
                print(f"  [{r['recall']:.0%}] {r['query'][:55]}  {status}{fb}")

            avg = sum(r["recall"] for r in results_sf) / len(results_sf) if results_sf else 0
            avg_lat = sum(r["latency_ms"] for r in results_sf) / len(results_sf) if results_sf else 0
            total_cost = sum(r["cost"] for r in results_sf)
            total_fb = sum(r["fallback_calls"] for r in results_sf)
            print(f"\n  Average recall: {avg:.0%}  |  Avg latency: {avg_lat:.0f}ms  |  Total cost: ${total_cost:.4f}  |  Fallback calls: {total_fb}")

        if args.live:
            label_live = f"{suite['name']} (jev)"
            print(f"\n{'='*60}")
            print(f"Running: {label_live}")
            print(f"{'='*60}")

            results_live = _run_suite(suite, live=True, top_k=args.top_k, threshold=args.threshold, max_queries=args.max_queries)
            all_results[label_live] = results_live

            for r in results_live:
                status = "[ok]" if r["recall"] == 1.0 else f"[missed: {r['missed']}]"
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
