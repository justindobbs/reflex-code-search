"""Analyze false accepts across all benchmark suites.

Categorizes each false-accept file by type (test, doc, tool, config, other)
and prints a summary to guide precision improvements.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from reflex_search.scorers import LocalScorer
from reflex_search.searcher import ReflexCodeSearcher


def _categorize(file_path: str) -> str:
    lf = file_path.lower()
    if "/test" in lf or lf.startswith("test"):
        return "test"
    if lf.endswith((".md", ".rst", ".txt")):
        return "doc"
    if "/tools/" in lf or lf.startswith("tools/"):
        return "tool"
    if lf.endswith((".toml", ".cfg", ".ini", ".json", ".yml", ".yaml")):
        return "config"
    return "other"


def main() -> None:
    data = json.loads((_PROJECT_ROOT / "benchmarks" / "queries.json").read_text())
    cats: dict[str, int] = {"test": 0, "doc": 0, "tool": 0, "config": 0, "other": 0}
    all_fa: list[tuple[str, float]] = []
    gap_data: list[dict] = []
    total_fa = 0
    total_slots = 0
    total_true = 0

    for suite in data["suites"]:
        root = str((_PROJECT_ROOT / suite["repo_root"]).resolve())
        print(f"\n{'='*60}")
        print(f"Suite: {suite['name']}")
        print(f"{'='*60}")

        for entry in suite["queries"]:
            query = entry["query"]
            expected = {p.replace("\\", "/") for p in entry["expected_files"]}

            scorer = LocalScorer()
            searcher = ReflexCodeSearcher(
                repo_root=root,
                scorer=scorer,
                top_k=5,
                accept_threshold=0.30,
                uncertain_threshold=0.10,
            )
            session = searcher.search(query)
            results = [(r.path.replace("\\", "/"), r.score) for r in session.results]
            returned_paths = {p for p, _ in results}

            hits = returned_paths & expected
            false_accepts = [(p, s) for p, s in results if p not in expected]
            total_slots += 5
            total_true += len(hits)
            total_fa += len(false_accepts)

            # Collect score-gap data for cutoff simulation
            if results:
                top_score = results[0][1]
                items = [(p, s, p in expected) for p, s in results]
                gap_data.append({"top_score": top_score, "items": items})

            if false_accepts:
                print(f"\n  Q: {query}")
                print(f"     Expected: {sorted(expected)}")
                print(f"     Hits: {len(hits)}/{len(expected)}")
                for fa_path, fa_score in false_accepts:
                    cat = _categorize(fa_path)
                    cats[cat] += 1
                    all_fa.append((fa_path, fa_score))
                    print(f"     FA: {fa_path}  score={fa_score:.3f}  [{cat}]")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total top-5 slots:    {total_slots}")
    print(f"True positives:       {total_true}")
    print(f"False accepts:        {total_fa}")
    print(f"Empty slots:          {total_slots - total_true - total_fa}")
    print(f"Precision@5:          {total_true / total_slots:.1%}")
    print()
    print("False accepts by category:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:10s}: {count:3d}  ({count / max(total_fa, 1):.0%})")

    # Sub-breakdown of "other"
    init_fa = sum(1 for p, _ in all_fa if p.endswith("__init__.py"))
    example_fa = sum(1 for p, _ in all_fa if "/examples/" in p or p.startswith("examples/"))
    print()
    print("Sub-breakdown of 'other':")
    print(f"  __init__.py : {init_fa}")
    print(f"  examples/   : {example_fa}")

    # Score-gap cutoff simulation
    print()
    print("Score-gap cutoff simulation (drop results below X% of top score):")
    for pct in (40, 50, 60, 70):
        cut_tp = 0
        cut_fa = 0
        kept_tp = 0
        kept_fa = 0
        for entry_data in gap_data:
            top_score = entry_data["top_score"]
            threshold = top_score * pct / 100
            for path, score, is_tp in entry_data["items"]:
                if score < threshold:
                    if is_tp:
                        cut_tp += 1
                    else:
                        cut_fa += 1
                else:
                    if is_tp:
                        kept_tp += 1
                    else:
                        kept_fa += 1
        new_prec = kept_tp / (kept_tp + kept_fa) if (kept_tp + kept_fa) else 0
        print(
            f"  {pct}%: drop {cut_fa} FA + {cut_tp} TP | "
            f"keep {kept_tp} TP + {kept_fa} FA | "
            f"precision={new_prec:.1%}"
        )


if __name__ == "__main__":
    main()
